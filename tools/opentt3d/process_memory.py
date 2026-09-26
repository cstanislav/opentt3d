"""Process memory sampling for bounded native renderer smoke runs."""

import ctypes
import json
from pathlib import Path
import platform
import time


class DarwinUsage(ctypes.Structure):
    # rusage_info_v0, sys/resource.h. Footprint includes compressed/GPU memory
    # that an RSS-only limit would miss on Apple silicon.
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [
        (name, ctypes.c_uint64) for name in (
            "user_time", "system_time", "idle_wakeups", "interrupt_wakeups",
            "pageins", "wired_size", "resident_size", "phys_footprint",
            "start_time", "exit_time")]


class DarwinTimebase(ctypes.Structure):
    _fields_ = [("numer", ctypes.c_uint32), ("denom", ctypes.c_uint32)]


class MemoryMonitor:
    def __init__(self, output, limit_mib):
        self.output = Path(output)
        self.limit = limit_mib * 1024 * 1024
        self.started = time.monotonic()
        self.peak = 0
        self.samples = 0
        self.exceeded = False
        self.system = platform.system()
        if self.system == "Darwin":
            self.libproc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
            self.libproc.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
            self.libproc.proc_pid_rusage.restype = ctypes.c_int
            system = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
            system.mach_timebase_info.argtypes = [ctypes.POINTER(DarwinTimebase)]
            timebase = DarwinTimebase()
            if system.mach_timebase_info(ctypes.byref(timebase)) != 0 or not timebase.denom:
                raise RuntimeError("Cannot read macOS CPU timebase")
            self.cpu_seconds_per_tick = timebase.numer / timebase.denom / 1e9
        elif self.system != "Linux":
            raise RuntimeError("Memory monitoring currently requires macOS or Linux")
        self.log = (self.output / "memory.jsonl").open("w", buffering=1)

    def sample(self, pid):
        if self.system == "Darwin":
            usage = DarwinUsage()
            if self.libproc.proc_pid_rusage(pid, 0, ctypes.byref(usage)) != 0:
                raise OSError(ctypes.get_errno(), "Cannot sample game memory")
            values = {"rss_bytes": usage.resident_size, "footprint_bytes": usage.phys_footprint,
                      "cpu_seconds": (usage.user_time + usage.system_time) * self.cpu_seconds_per_tick}
        else:
            status = dict(line.split(":", 1) for line in Path(f"/proc/{pid}/status").read_text().splitlines())
            rss = int(status["VmRSS"].split()[0]) * 1024
            swap = int(status.get("VmSwap", "0").split()[0]) * 1024
            values = {"rss_bytes": rss, "rss_swap_bytes": rss + swap}
        used = max(value for key, value in values.items() if key.endswith("_bytes"))
        self.peak = max(self.peak, used)
        self.samples += 1
        self.log.write(json.dumps({"seconds": time.monotonic() - self.started, "pid": pid, **values}) + "\n")
        if used > self.limit:
            self.exceeded = True
            raise RuntimeError(f"Game memory {used / 1048576:.1f} MiB exceeds {self.limit / 1048576:.1f} MiB limit; see memory.jsonl")

    def close(self):
        self.log.close()
        (self.output / "memory-summary.json").write_text(json.dumps({
            "limit_bytes": self.limit, "peak_sampled_bytes": self.peak,
            "samples": self.samples, "limit_exceeded": self.exceeded,
        }, indent=2) + "\n")

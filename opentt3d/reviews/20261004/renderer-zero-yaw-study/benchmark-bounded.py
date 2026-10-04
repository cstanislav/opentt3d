"""Bounded actual saved-size1 timing/memory observations; never infer sustained60fps."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BUILD=ROOT/'build-macos'


def main():
    assert not (HERE/'benchmark-runs.json').exists()
    fixture=BUILD/'breadth-original-hq-natural-upgrade-temperate-costed-town-service-study'
    records=[];observations=[]
    # Run only after renderer correctness matrices finish, without concurrent
    # local GPU review jobs. Background mode is quiet, not foreground acceptance.
    proof=json.loads((HERE/'supplement-verification.json').read_text());assert proof['noninterference_accepted']
    for backend in ('vulkan','opengl'):
        output=BUILD/f'breadth-original-zero-yaw-size1-{backend}-bounded-timing'
        command=[sys.executable,'tools/opentt3d/smoke.py','--build-dir',str(BUILD),'--output',str(output),
            '--background','--no-hidpi','--record-console','--synchronous-save','--blitter','40bpp-anim','--backend',backend,
            '--savegame',str(fixture/'save/hq-natural-final.sav'),'--ai-dir',str(fixture/'ai'),
            '--reference-object','4','--reference-object-tile','8','8','--zoom','0','--resolution','640','480',
            '--benchmark-frames','1800','--running','--memory-limit-mib','6144','--timeout','600','--brief']
        with (HERE/(output.name+'.log')).open('x') as log:
            process=subprocess.run(command,cwd=ROOT,env=dict(os.environ,OPENTT3D_BACKGROUND='1'),stdout=log,stderr=subprocess.STDOUT)
        records.append({'output':str(output.relative_to(ROOT)),'backend':backend,'command':command,'exit_code':process.returncode})
        (HERE/'benchmark-runs.json').write_text(json.dumps(records,indent=2)+'\n')
        if process.returncode:raise SystemExit(process.returncode)
        benchmark=json.loads((output/'benchmark.json').read_text());memory=json.loads((output/'memory-summary.json').read_text())
        assert benchmark['frames']==1800 and not memory['limit_exceeded']
        observations.append({'backend':backend,'actual_saved_size1_world':True,'quiet_background_only':True,
            'measured_fps':benchmark['measured_fps'],'intervals_over_20_ms':benchmark['intervals_over_20_ms'],
            'frame_interval_ms':benchmark['frame_interval_ms'],'frame_work_ms':benchmark['frame_work_ms'],
            'peak_sampled_bytes':memory['peak_sampled_bytes'],'samples':memory['samples'],
            'no_speedup_inferred_without_an_independent_paired_baseline':True,'sustained_60fps_accepted':False})
    value={'observed_utc':datetime.now(timezone.utc).isoformat(),'observations':observations,'frames_per_backend':1800,
        'all_families_resolution_platforms_world_sizes_foreground_input_or_60fps_accepted':False,'quality_approvals':0}
    (HERE/'bounded-timing.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))


if __name__=='__main__':main()

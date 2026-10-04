"""Unchanged smoke harness with independent APFS clones for disposable fixture copies."""
import ctypes
import os
from pathlib import Path
import runpy
import shutil
import sys

ROOT=Path(__file__).resolve().parents[4]
original=shutil.copyfile
clone=ctypes.CDLL(None,use_errno=True).clonefile
clone.argtypes=(ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int)
clone.restype=ctypes.c_int


def copyfile(source,destination,*,follow_symlinks=True):
    if follow_symlinks and os.path.isfile(source) and not os.path.lexists(destination):
        if clone(os.fsencode(source),os.fsencode(destination),0)==0:return destination
    return original(source,destination,follow_symlinks=follow_symlinks)


shutil.copyfile=copyfile
sys.path.insert(0,str(ROOT/'tools/opentt3d'))
runpy.run_path(str(ROOT/'tools/opentt3d/smoke.py'),run_name='__main__')

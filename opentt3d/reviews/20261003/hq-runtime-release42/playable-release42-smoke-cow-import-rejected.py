"""Run the unchanged smoke harness; APFS-clone only newly copied fixture resources."""
import ctypes,os,runpy,shutil

original=shutil.copyfile;clone=ctypes.CDLL(None,use_errno=True).clonefile
clone.argtypes=(ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int);clone.restype=ctypes.c_int
def copyfile(source,destination,*,follow_symlinks=True):
    if follow_symlinks and os.path.isfile(source) and not os.path.lexists(destination):
        if clone(os.fsencode(source),os.fsencode(destination),0)==0:return destination
    return original(source,destination,follow_symlinks=follow_symlinks)
shutil.copyfile=copyfile
runpy.run_path('tools/opentt3d/smoke.py',run_name='__main__')

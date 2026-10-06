"""Temporary Windows execution request until the owned measurement exits."""
import argparse
import ctypes
import json
from datetime import datetime,timezone
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--measurement-pid',type=int,required=True)
args=parser.parse_args()
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.SetThreadExecutionState.argtypes=[ctypes.c_uint32]
kernel.SetThreadExecutionState.restype=ctypes.c_uint32
kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
kernel.OpenProcess.restype=ctypes.c_void_p
kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
audit=Path(__file__).resolve().parents[1]/'audit/project2-v1'

def receipt(name,value):
    value['time_utc']=datetime.now(timezone.utc).isoformat()
    (audit/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

handle=kernel.OpenProcess(0x100000,False,args.measurement_pid)
if not handle: raise ctypes.WinError(ctypes.get_last_error())
try:
    result=kernel.SetThreadExecutionState(0x80000001)
    if not result: raise ctypes.WinError(ctypes.get_last_error())
    receipt('v03_power_request_active.json',{'status':'active','return_flags':result,'measurement_pid':args.measurement_pid,'scope':'temporary system-required request; no display or policy change'})
    while kernel.WaitForSingleObject(handle,20000)==0x102:
        pass
finally:
    kernel.SetThreadExecutionState(0x80000000)
    kernel.CloseHandle(handle)
    receipt('v03_power_request_released.json',{'status':'released'})

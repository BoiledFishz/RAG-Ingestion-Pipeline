"""Real owned subprocess cancellation, without model/corpus fabrication."""
import ctypes
import os
import subprocess
import sys
from agents.project2.rag_process import BoundedRAGProcess

def alive(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x100000,False,pid)
    if not handle:return False
    try:return kernel.WaitForSingleObject(ctypes.c_void_p(handle),0)==0x102
    finally:kernel.CloseHandle(ctypes.c_void_p(handle))

def test_real_cancellation_stops_owned_descendants_before_closing_pipes():
    leaf='import time; time.sleep(60)'
    parent='import subprocess,sys,time; p=subprocess.Popen([sys.executable,"-c",'+repr(leaf)+'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True); time.sleep(60)'
    process=subprocess.Popen([sys.executable,'-c',parent],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    leaf_pid=int(process.stdout.readline());runtime=BoundedRAGProcess({'AGENT_MODEL':'qwen2.5:7b'});runtime.process=process
    try:
        assert alive(leaf_pid)
        runtime.stop()
        assert not alive(leaf_pid), 'Cancellation killed the launcher but left an owned descendant running'
    finally:
        if alive(leaf_pid):subprocess.run([os.path.join(os.environ['WINDIR'],'System32','taskkill.exe'),'/PID',str(leaf_pid),'/T','/F'],capture_output=True)
        if process.poll() is None:process.kill();process.wait(timeout=5)

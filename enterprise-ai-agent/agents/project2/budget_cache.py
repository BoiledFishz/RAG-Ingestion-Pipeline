"""Verify once, then deny writes/deletes to every source for this service lifetime.

This caches immutable server configuration only, never queries or worker results.
Non-Windows runtimes keep the full per-request verifier until an equivalent
mandatory file-lock strategy is available.
"""
from __future__ import annotations
import atexit
import ctypes
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Callable


class ReadLocks:
    def __init__(self, paths: list[Path]) -> None:
        self.handles: list[Any] = []
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        from ctypes import wintypes
        kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        kernel.CreateFileW.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.kernel=kernel
        try:
            for path in paths:
                handle=kernel.CreateFileW(str(path),0x80000000,1,None,3,0x80,None)
                if handle==ctypes.c_void_p(-1).value:
                    raise ctypes.WinError(ctypes.get_last_error())
                self.handles.append(handle)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        for handle in self.handles:self.kernel.CloseHandle(handle)
        self.handles.clear()

    def __enter__(self) -> ReadLocks:return self
    def __exit__(self, *args: Any) -> None:self.close()


def sources(root: Path) -> list[Path]:
    folder=root/'evals/project2-v1/calibration_v031'
    def read(path: Path) -> dict:return json.loads(path.read_text(encoding='utf-8'))
    decision=read(folder/'decision.json')
    target=folder/f"batch{decision['selected_batch']}"
    protocol=read(folder/'protocol.json')
    docs=root/'specs/project2/v0.3.1'
    paths={folder/'budget_frozen.json',folder/'frozen_manifest.json',target/'frozen_manifest.json',docs/'version_manifest.json'}
    paths.update(folder/name for name in read(folder/'frozen_manifest.json')['files'])
    paths.update(target/name for name in read(target/'frozen_manifest.json')['files'])
    paths.update(root/name for name in {**protocol['protected_files'],**protocol['batch1_files']})
    paths.update(docs/name for name in read(docs/'version_manifest.json')['files'])
    paths={path.resolve() for path in paths}
    if any(not path.is_relative_to(root.resolve()) for path in paths):
        raise ValueError('Frozen budget source escaped workspace')
    return sorted(paths)


_LOCK=RLock()
_CONFIG: dict[Path, tuple[dict[str, Any], ReadLocks]] = {}


def verified_limits(root: Path, verifier: Callable[[Path], dict[str, Any]]) -> dict[str, Any]:
    root=root.resolve()
    if os.name!='nt' or not (root/'evals/project2-v1/calibration_v031/budget_frozen.json').is_file():
        return verifier(root)
    with _LOCK:
        if root not in _CONFIG:
            paths=sources(root)
            locked=ReadLocks(paths)
            try:
                if sources(root)!=paths:raise ValueError('Frozen source set changed during service startup')
                limits=verifier(root)  # Complete hashes checked AFTER acquiring every read lock.
                _CONFIG[root]=(dict(limits),locked)
                atexit.register(locked.close)
            except BaseException:
                locked.close()
                raise
        return dict(_CONFIG[root][0])

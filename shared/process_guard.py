"""Single-process startup guard for long-running AgeKeeper modules (Windows)."""

import atexit
import ctypes
from ctypes import wintypes

ERROR_ALREADY_EXISTS = 183
_MUTEX_HANDLE = None

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_CreateMutexW = _kernel32.CreateMutexW
_CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
_CreateMutexW.restype = wintypes.HANDLE

_CloseHandle = _kernel32.CloseHandle
_CloseHandle.argtypes = [wintypes.HANDLE]
_CloseHandle.restype = wintypes.BOOL


def release_single_instance_lock() -> None:
    """Release the process-wide instance lock if currently held."""
    global _MUTEX_HANDLE
    if _MUTEX_HANDLE:
        _CloseHandle(_MUTEX_HANDLE)
        _MUTEX_HANDLE = None


def acquire_single_instance_lock(name: str = "AgeKeeper.Instance") -> bool:
    """Return True if this process acquired the single-instance lock."""
    global _MUTEX_HANDLE
    if _MUTEX_HANDLE:
        return True

    handle = _CreateMutexW(None, False, name)
    if not handle:
        raise OSError("Failed to create process mutex")

    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        _CloseHandle(handle)
        return False

    _MUTEX_HANDLE = handle
    atexit.register(release_single_instance_lock)
    return True


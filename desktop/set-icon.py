"""Embed icon.png in a Windows executable. Build-time only; requires Pillow."""
import ctypes
from ctypes import wintypes as W
import io
from pathlib import Path
import struct
import sys
from PIL import Image


def embed(executable, png):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LoadLibraryExW.argtypes = [W.LPCWSTR, W.HANDLE, W.DWORD]
    kernel.LoadLibraryExW.restype = W.HMODULE
    kernel.FreeLibrary.argtypes = [W.HMODULE]
    name_callback = ctypes.WINFUNCTYPE(W.BOOL, W.HMODULE, ctypes.c_void_p, ctypes.c_void_p, W.LPARAM)
    lang_callback = ctypes.WINFUNCTYPE(W.BOOL, W.HMODULE, ctypes.c_void_p, ctypes.c_void_p, W.WORD, W.LPARAM)
    kernel.EnumResourceNamesW.argtypes = [W.HMODULE, ctypes.c_void_p, name_callback, W.LPARAM]
    kernel.EnumResourceLanguagesW.argtypes = [W.HMODULE, ctypes.c_void_p, ctypes.c_void_p, lang_callback, W.LPARAM]
    kernel.BeginUpdateResourceW.argtypes = [W.LPCWSTR, W.BOOL]
    kernel.BeginUpdateResourceW.restype = W.HANDLE
    kernel.UpdateResourceW.argtypes = [W.HANDLE, ctypes.c_void_p, ctypes.c_void_p, W.WORD, ctypes.c_void_p, W.DWORD]
    kernel.EndUpdateResourceW.argtypes = [W.HANDLE, W.BOOL]
    module = kernel.LoadLibraryExW(str(executable), None, 2)
    if not module:
        raise ctypes.WinError(ctypes.get_last_error())
    groups, icon_ids = [], []

    @name_callback
    def icons(_module, _kind, name, _param):
        if name < 65536:
            icon_ids.append(name)
        return True

    @name_callback
    def names(module, kind, name, _param):
        value = name if name < 65536 else ctypes.wstring_at(name)

        @lang_callback
        def languages(_module, _kind, _name, lang, _param):
            groups.append((value, lang))
            return True

        kernel.EnumResourceLanguagesW(module, kind, name, languages, 0)
        return True

    try:
        kernel.EnumResourceNamesW(module, 3, icons, 0)
        kernel.EnumResourceNamesW(module, 14, names, 0)
    finally:
        kernel.FreeLibrary(module)
    if not groups:
        groups = [(1, 1033)]
    first_id = max(icon_ids, default=0) + 1
    if first_id + 7 > 65535:
        raise ValueError('No free icon resource IDs')
    with Image.open(png) as source:
        source = source.convert('RGBA')
        # Pad rather than stretch a non-square source.
        edge = max(source.size)
        square = Image.new('RGBA', (edge, edge))
        square.paste(source, ((edge-source.width)//2, (edge-source.height)//2))
        frames = []
        for size in (16, 24, 32, 48, 64, 128, 256):
            stream = io.BytesIO()
            square.resize((size, size), Image.Resampling.LANCZOS).save(stream, format='PNG')
            frames.append((size, stream.getvalue()))
    group = struct.pack('<HHH', 0, 1, len(frames)) + b''.join(
        struct.pack('<BBBBHHIH', size % 256, size % 256, 0, 0, 1, 32, len(data), first_id+i)
        for i, (size, data) in enumerate(frames))
    update = kernel.BeginUpdateResourceW(str(executable), False)
    if not update:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        def write(kind, name, language, data):
            key = name if isinstance(name, int) else ctypes.cast(ctypes.c_wchar_p(name), ctypes.c_void_p)
            buf = ctypes.create_string_buffer(data)
            if not kernel.UpdateResourceW(update, kind, key, language, buf, len(data)):
                raise ctypes.WinError(ctypes.get_last_error())
        for language in {lang for _, lang in groups}:
            for i, (_, data) in enumerate(frames):
                write(3, first_id+i, language, data)
        for name, language in groups:
            write(14, name, language, group)
    except BaseException:
        kernel.EndUpdateResourceW(update, True)
        raise
    if not kernel.EndUpdateResourceW(update, False):
        raise ctypes.WinError(ctypes.get_last_error())
    print(f'Embedded {len(frames)} icon sizes in {executable}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('Usage: set-icon.py executable icon.png')
    embed(Path(sys.argv[1]).resolve(strict=True), Path(sys.argv[2]).resolve(strict=True))

# -*- mode: python ; coding: utf-8 -*-
# ponytail: sidecar CPU-only para el MVP — GPU/CUDA queda para después, el
# .so de llama_cpp compilado con CUDA es órdenes de magnitud más pesado.
from PyInstaller.utils.hooks import collect_all, collect_data_files

llama_datas, llama_binaries, llama_hiddenimports = collect_all("llama_cpp")
llm_datas = collect_data_files("llm")
django_datas, django_binaries, django_hiddenimports = collect_all("django")

a = Analysis(
    ["run_sidecar.py"],
    pathex=["."],
    binaries=llama_binaries + django_binaries,
    datas=llama_datas + llm_datas + django_datas,
    hiddenimports=llama_hiddenimports
    + django_hiddenimports
    + ["daphne", "corsheaders", "llm", "llm.services", "server.settings"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="llm-lab-server",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)

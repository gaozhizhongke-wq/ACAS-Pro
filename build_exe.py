#!/usr/bin/env python3
"""
ACAS Pro - Build Script
Creates standalone Windows executable
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def build():
    """Build standalone executable"""
    print("=" * 60)
    print("ACAS Pro - Build System")
    print("=" * 60)
    print()
    
    # Clean previous builds
    print("[1/5] Cleaning previous builds...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"  Removed {folder}/")
    
    # Install PyInstaller
    print("\n[2/5] Checking PyInstaller...")
    try:
        import PyInstaller
        print("  PyInstaller already installed")
    except ImportError:
        print("  Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Create spec file
    print("\n[3/5] Creating build configuration...")
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src', 'acas_pro')],
    hiddenimports=[
        'PySide6',
        'jwt',
        'cryptography',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ACAS-Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
'''
    with open("ACAS-Pro.spec", "w") as f:
        f.write(spec_content)
    print("  Created ACAS-Pro.spec")
    
    # Build
    print("\n[4/5] Building executable...")
    subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "ACAS-Pro.spec",
        "--clean",
        "--noconfirm"
    ], check=True)
    
    # Create installer
    print("\n[5/5] Creating installer package...")
    dist_dir = Path("dist") / "ACAS-Pro-Setup"
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy files
    shutil.copy("dist/ACAS-Pro.exe", dist_dir)
    shutil.copy("install.bat", dist_dir)
    shutil.copy("requirements.txt", dist_dir)
    
    # Create README
    readme = """# ACAS Pro - Enterprise Edition

## Installation

1. Run `install.bat` to install dependencies
2. Or run `ACAS-Pro.exe` directly (standalone)

## System Requirements

- Windows 10/11
- Python 3.10+ (for source installation)
- 4GB RAM minimum
- 500MB disk space

## Support

Contact: support@acas-tech.com
"""
    with open(dist_dir / "README.txt", "w") as f:
        f.write(readme)
    
    print("\n" + "=" * 60)
    print("Build Complete!")
    print("=" * 60)
    print(f"\nOutput: {dist_dir}")
    print("\nFiles:")
    for f in dist_dir.iterdir():
        print(f"  - {f.name}")
    print()


if __name__ == "__main__":
    try:
        build()
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        sys.exit(1)

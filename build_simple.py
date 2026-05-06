#!/usr/bin/env python3
"""
ACAS Pro - Simple Build Script
"""

import os
import sys
import subprocess
import shutil

def main():
    print("=" * 60)
    print("ACAS Pro - Build System")
    print("=" * 60)
    
    # Clean
    print("\n[1/3] Cleaning...")
    for d in ["build", "dist"]:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"  Removed {d}/")
    
    # Build with PyInstaller
    print("\n[2/3] Building executable...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "main.py")
    src_path = os.path.join(script_dir, "src")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "ACAS-Pro",
        "--add-data", f"{src_path};src",
        "--hidden-import", "PySide6",
        "--hidden-import", "jwt",
        "--hidden-import", "cryptography",
        "--hidden-import", "numpy",
        main_py
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR:", result.stderr)
        return 1
    
    print("  Build successful!")
    
    # Create distribution
    print("\n[3/3] Creating distribution...")
    dist_dir = "dist/ACAS-Pro-Enterprise"
    os.makedirs(dist_dir, exist_ok=True)
    
    shutil.copy("dist/ACAS-Pro.exe", dist_dir)
    shutil.copy("LICENSE.txt", dist_dir)
    
    # Create README
    with open(f"{dist_dir}/README.txt", "w") as f:
        f.write("""ACAS Pro Enterprise Edition v4.0.0
=====================================

QUICK START:
1. Run ACAS-Pro.exe to start the application
2. Create an account or use guest mode
3. Access Dashboard, Forecast, Inventory, and Intelligence modules

SYSTEM REQUIREMENTS:
- Windows 10/11 (64-bit)
- 4GB RAM minimum
- 500MB disk space

SUPPORT:
Email: support@acas-tech.com
Phone: +1-800-ACAS-PRO

(c) 2026 ACAS Technology. All rights reserved.
""")
    
    print(f"\n  Distribution created: {dist_dir}/")
    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print("=" * 60)
    print(f"\nOutput: {os.path.abspath(dist_dir)}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

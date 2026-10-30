#!/usr/bin/env python3
"""Build script for ghive to generate standalone executables using PyInstaller."""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def build():
    """Build standalone binary using PyInstaller."""
    root_dir = Path(__file__).resolve().parent.parent
    entry_point = root_dir / "ghive.py"
    src_dir = root_dir / "src"
    dist_dir = root_dir / "dist"
    build_dir = root_dir / "build"

    print("=== Building ghive executable ===")
    print(f"Target entry: {entry_point}")

    # Ensure PyInstaller is installed
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("PyInstaller not found. Installing via pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=ghive",
        f"--paths={src_dir}",
        str(entry_point),
    ]

    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(root_dir), check=True)

    print("\nBuild completed successfully!")
    print(f"Artifacts located in: {dist_dir / 'ghive'}")


if __name__ == "__main__":
    build()

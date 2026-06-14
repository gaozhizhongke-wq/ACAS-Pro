#!/usr/bin/env python3
"""
ACAS Pro - Setup Script
Enterprise Auto Customer Acquisition System
"""

from setuptools import setup, find_packages

setup(
    name="acas-pro",
    version="4.0.0",
    description="Enterprise Auto Customer Acquisition System",
    author="ACAS Technology",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "PySide6>=6.4.0",
        "pyjwt>=2.8.0",
        "cryptography>=41.0.0",
        "numpy>=1.24.0",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "acas-pro=main:main",
        ],
    },
)

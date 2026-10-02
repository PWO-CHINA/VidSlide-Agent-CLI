#!/usr/bin/env python3
"""Setup script for VidSlide Agent CLI."""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from package
version = {}
with open("src/vidslide/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            exec(line, version)
            break

# Read long description from README
long_description = Path("README.md").read_text(encoding="utf-8")

setup(
    name="vidslide-agent-cli",
    version=version.get("__version__", "0.1.0"),
    description="AI-native CLI tool for extracting PowerPoint slides from screen recordings",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="PWO-CHINA",
    author_email="dev@pwo-china.com",
    url="https://github.com/PWO-CHINA/VidSlide-Agent-CLI",
    project_urls={
        "Bug Reports": "https://github.com/PWO-CHINA/VidSlide-Agent-CLI/issues",
        "Source": "https://github.com/PWO-CHINA/VidSlide-Agent-CLI",
        "Documentation": "https://github.com/PWO-CHINA/VidSlide-Agent-CLI#readme",
    },
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "Topic :: Office/Business",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="video slides ppt extraction ai-agent cli automation",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "opencv-python>=4.5.0",
        "numpy>=1.20.0",
        "python-pptx>=0.6.21",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vidslide=vidslide.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)

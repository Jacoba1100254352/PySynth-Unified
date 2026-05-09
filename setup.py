#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = ["click>=8.0", "numpy>=1.21"]

test_requirements = [
    "coverage>=7",
    "pytest>=7",
]

setup(
    author="g4brielvs and PySynth Unified contributors",
    author_email="tomita@g4brielvs.me",
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ],
    description="Unified PySynth/Tomita command-line synthesizer",
    entry_points={
        "console_scripts": [
            "tomita=tomita.cli:main",
            "pysynth=pysynth.cli:main",
        ],
    },
    install_requires=requirements,
    license="GPL-3.0-only",
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/x-rst",
    include_package_data=True,
    keywords="pysynth tomita music synthesizer abc midi wav",
    name="pysynth-unified",
    packages=find_packages(include=["tomita", "tomita.*", "pysynth", "pysynth.*"]),
    extras_require={"test": test_requirements},
    project_urls={
        "Source": "https://github.com/Jacoba1100254352/PySynth-Unified",
        "Maintained upstream": "https://github.com/g4brielvs/PySynth",
        "Original PySynth": "https://github.com/mdoege/PySynth",
    },
    url="https://github.com/Jacoba1100254352/PySynth-Unified",
    version="0.3.0",
    zip_safe=False,
)

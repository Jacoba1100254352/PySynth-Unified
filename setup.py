#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = ["click>=8.0", "numpy>=1.21"]

test_requirements = [
    "pytest>=7",
]

setup(
    author="g4brielvs",
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
    description="PySynth/Tomita is a music and synthesizer package",
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
    keywords="pysynth tomita music synthesizer",
    name="tomita",
    packages=find_packages(include=["tomita", "tomita.*", "pysynth", "pysynth.*"]),
    extras_require={"test": test_requirements},
    url="https://github.com/g4brielvs/python-tomita",
    version="0.2.0",
    zip_safe=False,
)

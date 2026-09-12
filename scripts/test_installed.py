"""Run the compatibility suite against an installed, non-editable package."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    source = args.source.resolve()
    with tempfile.TemporaryDirectory(prefix="pysynth-installed-") as directory:
        work = Path(directory)
        shutil.copytree(source / "tests", work / "tests",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(source / "tomita/legacy/test_nokiacomposer2wav.py", work / "test_ringtone.py")
        subprocess.run([
            sys.executable, "-I", "-c",
            "import sys, pathlib, pysynth, tomita; "
            "from importlib.metadata import version; "
            "assert pysynth.__version__ == tomita.__version__ == version('pysynth-unified'); "
            "prefix = pathlib.Path(sys.prefix); "
            "assert pathlib.Path(tomita.__file__).resolve().is_relative_to(prefix); "
            "assert pathlib.Path(pysynth.__file__).resolve().is_relative_to(prefix); "
            "print('Installed version:', tomita.__version__)",
        ], cwd=work, check=True)
        scripts = Path(sysconfig.get_path("scripts"))
        for command in ("pysynth", "tomita"):
            executable = scripts / (command + (".exe" if os.name == "nt" else ""))
            subprocess.run([str(executable), "list-sounds"], cwd=work, check=True)
        subprocess.run([
            sys.executable, "-I", "-m", "pytest", "-q", "--import-mode=importlib",
            str(work / "tests"), str(work / "test_ringtone.py"),
        ], cwd=work, check=True)


if __name__ == "__main__":
    main()

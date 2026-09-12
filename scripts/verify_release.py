"""Inspect, install, and test source/wheel artifacts, then write SHA256SUMS."""

import argparse
from email.parser import BytesParser
import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


def check_names(names):
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name:
            raise ValueError("unsafe archive path: %s" % name)
        if any(part in (".git", ".venv", "__pycache__", ".pypirc", ".env")
               or (part.startswith(".env.") and part != ".env.example")
               or part.endswith((".pyc", ".pem", ".key")) for part in path.parts):
            raise ValueError("local/private artifact in archive: %s" % name)


def check_metadata(raw, expected):
    metadata = BytesParser().parsebytes(raw)
    for field, value in (("Name", "pysynth-unified"), ("Version", expected),
                         ("Requires-Python", ">=3.9")):
        if metadata[field] != value:
            raise ValueError("unexpected %s metadata: %r" % (field, metadata[field]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    stem = "pysynth_unified-" + args.version
    wheel = directory / (stem + "-py3-none-any.whl")
    sdist = directory / (stem + ".tar.gz")
    required = {
        "README.rst", "HISTORY.rst", "LICENSE", "CONTRIBUTING.rst",
        "pyproject.toml", "setup.py", "setup.cfg", "Makefile", "tox.ini",
        "pysynth.example.json", "docs/conf.py", "docs/index.rst",
        "tests/test_tomita.py", "tests/test_release_compatibility.py",
        "scripts/test_installed.py", "scripts/verify_release.py", "RELEASE_NOTES.md",
    }
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        check_names(names)
        check_metadata(archive.read(stem + ".dist-info/METADATA"), args.version)
        if not any(name.endswith("/LICENSE") for name in names):
            raise ValueError("wheel is missing its license")
        wheel_modules = {name for name in names if name.endswith(".py")}
    with tempfile.TemporaryDirectory(prefix="pysynth-release-") as temporary:
        work = Path(temporary)
        with tarfile.open(sdist) as archive:
            members = archive.getmembers()
            check_names(member.name for member in members)
            if any(not (member.isfile() or member.isdir()) for member in members):
                raise ValueError("source archive contains a link or special file")
            if any(PurePosixPath(member.name).parts[0] != stem for member in members):
                raise ValueError("source archive has an unexpected root")
            names = {str(PurePosixPath(member.name).relative_to(stem)) for member in members}
            missing = (required | wheel_modules) - names
            if missing:
                raise ValueError("source archive is missing: %s" % sorted(missing))
            check_metadata(archive.extractfile(stem + "/PKG-INFO").read(), args.version)
            archive.extractall(work, filter="data")
        source = work / stem
        for kind, artifact in (("wheel", wheel), ("sdist", sdist)):
            environment = work / (kind + "-env")
            venv.EnvBuilder(with_pip=True).create(environment)
            executable = environment / (
                "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
            )
            subprocess.run([str(executable), "-m", "pip", "install", str(artifact) + "[test]"],
                           check=True)
            subprocess.run([str(executable), str(source / "scripts/test_installed.py"),
                            "--source", str(source)], cwd=work, check=True)
            subprocess.run([str(executable), "-m", "pip", "check"], check=True)
        # Build documentation from the archive itself using the caller's dev tools.
        subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-b", "html",
                        str(source / "docs"), str(work / "html")], cwd=source, check=True)
    checksums = "".join("%s  %s\n" % (hashlib.sha256(path.read_bytes()).hexdigest(), path.name)
                        for path in (wheel, sdist))
    (directory / "SHA256SUMS").write_text(checksums, encoding="ascii")
    print("Verified wheel, source archive, installed compatibility tests, and documentation.")
    print(checksums, end="")


if __name__ == "__main__":
    main()

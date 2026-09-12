# PySynth Unified 0.3.1

This release consolidates the unified PySynth/Tomita API and CLI with input
validation, legacy compatibility fixes, and verified source and wheel packages.
It is the first GitHub release of this fork. Version 0.3.1 advances the existing
0.3.0 package version without removing legacy imports or console commands.

## Changes

- Validate songs, durations, sound names, configuration, and progress options
  before rendering, with actionable command-line errors.
- Keep `pysynth` and `tomita` commands and public facades aligned. Route legacy
  ABC/MIDI helpers through the unified renderer; preserve their old arguments.
- Fix beeper flats, dotted values, repeats, and accent-marker handling.
- Map demo articulation to the piano engines' legato option so built-in demos
  work across sound choices.
- Correct sampler frame counts, signed 24-bit decoding, adjacent-key resampling,
  and octave transposition. Handle short samples and silent songs, honor quiet
  mode, and preserve existing output when required sample files are invalid.
- Harden MIDI event parsing, running status, system-exclusive messages, metadata,
  malformed-file errors, and zero-duration handling.
- Complete the source archive with documentation configuration, an example
  config, test tooling, and release instructions. Add installed-package tests
  and checksums for both distribution formats.

## Compatibility and verification

The release matrix covers CPython 3.9–3.14 on Linux and 3.14 on macOS and
Windows. Python 3.9 is retained for existing users; prefer a maintained Python
runtime for new installs. All nine engine imports, actual WAV rendering, public
APIs, CLI commands, and legacy ABC/MIDI entrypoints are exercised. Source and
wheel installations are tested outside the checkout, and documentation is built
from the source archive.

The MIDI/ABC readers retain their melody-oriented limitations; full polyphony,
tempo maps, and controller/sustain playback are not supported. Legacy interactive
playback is retained but not covered by the release gate. The `samp` engine needs
separately obtained Salamander 48 kHz, 24-bit stereo PCM files; automated tests use
generated audio fixtures in that format. Beeper accepts accents without changing
volume. Invalid inputs that previously produced partial files or raw tracebacks
now fail with clear errors.

## Install

Download `pysynth_unified-0.3.1-py3-none-any.whl`, or the source archive
`pysynth_unified-0.3.1.tar.gz`, and `SHA256SUMS` from this release. Check the
download hashes, then install in a virtual environment:

```console
python -m pip install pysynth_unified-0.3.1-py3-none-any.whl
pysynth list-sounds
pysynth --song "4c4 4e4 4g4 2c5" --sound e --output example.wav
```

The source archive installs with the same pip command using its filename.
This is a GitHub distribution release; no PyPI publication is implied.

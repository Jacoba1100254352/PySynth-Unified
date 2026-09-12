=======
History
=======

0.3.1 (2026-09-12)
------------------

* Validate songs and configuration before rendering, with clear CLI errors.
* Route the legacy ABC and MIDI helpers through the unified renderer.
* Harden MIDI parsing and keep ``--quiet`` output quiet for metadata events.
* Add maintained API documentation, package checks, and multi-version CI.
* Fix beeper accents and map demo articulation to the piano engines.
* Correct sample decoding, frame counts, transposition, and short/silent sample
  handling; validate sample files before opening the output.
* Test all nine legacy and unified engines, legacy file entrypoints, and
  installed distributions outside the checkout.
* Complete source-archive documentation/tooling, add artifact verification and
  checksums, and test Python 3.9--3.14 plus macOS/Windows compatibility.
* Publish the first GitHub release of this fork with documented release gates
  and explicit MIDI, ABC, sample-library, and playback limitations.

0.3.0 (2026-05-01)
------------------

* Publish PySynth Unified package metadata.
* Add the unified ``pysynth`` command, sound selection, ABC/MIDI rendering,
  config helpers, and adaptive progress output.
* Keep the ``tomita`` namespace and command for compatibility.

0.2.0 (2020-05-03)
------------------

* Add module with legacy scripts

0.1.0 (2020-05-02)
------------------

* First release on PyPI.

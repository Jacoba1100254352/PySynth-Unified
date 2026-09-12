====================
Legacy compatibility
====================

The original engines remain importable under ``tomita.legacy``. Existing code
can continue to import modules such as ``tomita.legacy.pysynth`` and
``tomita.legacy.pysynth_b``. New code should normally call
``pysynth.make_wav`` so sound selection, validation, sample paths, and progress
behavior are handled consistently.

Both console names and ``python -m pysynth.cli`` / ``python -m tomita.cli``
use the same interface. Legacy file helpers can still be run as modules::

    python -m tomita.legacy.read_abc tune.abc 1 --sound=beeper
    python -m tomita.legacy.readmidi tune.mid 0 tune.wav --sound=e

The ABC helper defaults to tune 1 and writes ``out.wav``. The legacy MIDI
helper retains its historical default of track 1; pass ``0`` explicitly for a
single-track file. The unified ``pysynth render`` command instead automatically
selects the first nonempty note track.

Regression tests exercise all nine engine imports and actual WAV rendering,
Nokia notation parsing, both file-reader module entrypoints, and both public
package facades. Legacy desktop playback and the interactive ``menv`` shell
are retained but are not part of the automated release benchmark.

ABC reader
----------

.. autofunction:: tomita.legacy.read_abc.abc_to_song

MIDI reader
-----------

.. autofunction:: tomita.legacy.readmidi.midi_to_song

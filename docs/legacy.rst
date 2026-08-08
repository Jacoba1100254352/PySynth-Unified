====================
Legacy compatibility
====================

The original engines remain importable under ``tomita.legacy``. Existing code
can continue to import modules such as ``tomita.legacy.pysynth`` and
``tomita.legacy.pysynth_b``. New code should normally call
``pysynth.make_wav`` so sound selection, validation, sample paths, and progress
behavior are handled consistently.

ABC reader
----------

.. autofunction:: tomita.legacy.read_abc.abc_to_song

MIDI reader
-----------

.. autofunction:: tomita.legacy.readmidi.midi_to_song

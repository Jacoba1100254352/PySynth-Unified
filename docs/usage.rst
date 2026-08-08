=====
Usage
=====

Python API
----------

Import the public facade and pass a sequence of ``(note, duration)`` pairs:

.. code-block:: python

    from pysynth import make_wav

    song = [
        ("c4", 4),
        ("d4", 4),
        ("e4", 4),
        ("r", 8),
        ("g4*", -4),
    ]

    make_wav(song, sound="e", bpm=120, fn="song.wav")

``1`` is a whole note, ``2`` is a half note, ``4`` is a quarter note, and so
on. ``r`` is a rest, ``*`` accents a note, and a negative duration is the
legacy shorthand for a dotted note. Sound names and aliases are available
through ``pysynth.available_sounds()`` and ``pysynth list-sounds``.

Command line
------------

Render inline notation or a built-in demo:

.. code-block:: console

    $ pysynth --song "4c4 4e4 4g4 2c5" --sound piano --output chord.wav
    $ pysynth --demo anthem --sound a --output anthem.wav

Render ABC and MIDI files:

.. code-block:: console

    $ pysynth render tune.abc --abc-song-number 1 --output tune.wav
    $ pysynth render tune.mid --track 0 --sound e --output tune.wav

If ``--track`` is omitted, the first MIDI track containing notes is selected.
Use ``--quiet`` for no progress or summary output, or ``--no-summary`` to keep
progress while hiding the final WAV summary.

Configuration
-------------

Create, inspect, and validate a config file with:

.. code-block:: console

    $ pysynth config init
    $ pysynth config show
    $ pysynth config validate

The default filename is ``pysynth.json``. It can define ``sound``,
``sample_path``, and progress settings. Pass a different file with
``--config path/to/config.json``.

Sample-backed piano
-------------------

The ``samp`` sound needs a local Salamander piano sample directory. Set it in
``pysynth.json``, pass ``--sample-path``, or set ``PYSYNTH_SAMPLE_PATH``. The
other sounds do not require external audio files.

===============
PySynth Unified
===============

*PySynth Unified* is a command-line music and synthesizer package based on the
maintained ``g4brielvs/PySynth`` fork of PySynth. It keeps the Tomita
package namespace for compatibility and also exposes a ``pysynth`` command and
Python facade.

* Free software: GNU General Public License v3
* Source repository: https://github.com/Jacoba1100254352/PySynth-Unified

About
-----

Isao Tomita (冨田 勲, Tomita Isao, 22 April 1932 – 5 May 2016), also known
mononymically as Tomita, was a Japanese composer and a pioneer of electronic
music and analog-synthesizer arrangements. `Wikipedia
<https://en.wikipedia.org/wiki/Isao_Tomita>`_


Features
--------

* Bundles the legacy PySynth engines in one importable package.
* Adds a unified ``pysynth``/``tomita`` command-line renderer.
* Supports sound selection through a config file or ``--sound`` option.
* Renders inline note strings, built-in demos, ABC files, and MIDI files from
  the same command-line interface.
* Includes preview and config helpers for comparing sounds and managing
  defaults.
* Uses configurable progress reporting that prints every note for small songs,
  throttles larger songs, and always prints the final ``[n/n]`` update.

Installation
------------

For a command-line install on macOS/Homebrew Python, use ``pipx``. It creates
an isolated environment and avoids Python's ``externally-managed-environment``
error:

.. code-block:: console

    $ brew install pipx
    $ pipx ensurepath
    $ export PATH="$HOME/.local/bin:$PATH"
    $ pipx install "git+https://github.com/Jacoba1100254352/PySynth-Unified.git"
    $ pysynth list-sounds

``pipx ensurepath`` updates your shell startup files, but the change may not
affect the terminal window you already have open. The ``export`` line above
makes ``pysynth`` available immediately; opening a new terminal after
``pipx ensurepath`` has the same effect.

If you installed this repo before version ``0.3.0`` and pipx reported
``installed package tomita 0.2.0``, replace that older pipx environment once:

.. code-block:: console

    $ pipx uninstall tomita
    $ pipx install "git+https://github.com/Jacoba1100254352/PySynth-Unified.git"

For Python code in VS Code or another editor, install into the project rather
than with ``pipx``. Create and activate a virtual environment in your project,
then install PySynth Unified into it:

.. code-block:: console

    $ python3 -m venv .venv
    $ . .venv/bin/activate
    $ python -m pip install -U pip
    $ python -m pip install "git+https://github.com/Jacoba1100254352/PySynth-Unified.git"

Select that ``.venv`` as the project's Python interpreter in your editor.

If you prefer the clone-and-install style used by older PySynth instructions,
use ``make install`` from the repo root. This installs into a local ``.venv``
so it also avoids system Python restrictions:

.. code-block:: console

    $ git clone https://github.com/Jacoba1100254352/PySynth-Unified.git
    $ cd PySynth-Unified
    $ make install
    $ .venv/bin/pysynth list-sounds

For isolated local development, clone the repo and install it into a virtual
environment instead:

.. code-block:: console

    $ git clone https://github.com/Jacoba1100254352/PySynth-Unified.git
    $ cd PySynth-Unified
    $ python -m venv .venv
    $ . .venv/bin/activate
    $ python -m pip install -U pip
    $ python -m pip install .

If you are already inside an activated virtual environment, ``make
install-active`` installs into that environment. This repo intentionally avoids
the older ``python3 setup.py install`` pattern so dependencies and console
scripts are installed through Python's supported packaging path.

After installation, verify the command-line entrypoint:

.. code-block:: console

    $ pysynth list-sounds
    $ pysynth --demo anthem --output pysynth_anthem.wav

PySynth
-------

All scripts from *PySynth* can be found as modules.

Python API
~~~~~~~~~~

The public ``pysynth`` facade is the simplest way to render from Python:

.. code-block:: python

    from pysynth import make_wav

    song = [
        ("c4", 4),
        ("d4", 4),
        ("e4", 4),
        ("g4", 4),
        ("c5", 2),
    ]

    make_wav(song, sound="e", bpm=120, fn="my_song.wav")

Durations use note denominators: ``1`` is a whole note, ``2`` a half note,
``4`` a quarter note, and so on. Use ``r`` for a rest, append ``*`` to accent a
note, and use a negative duration for the legacy dotted-note shorthand (for
example, ``-4`` is a dotted quarter note).

Unified renderer
~~~~~~~~~~~~~~~~

Render the built-in anthem demo with the default PySynth A sound:

.. code-block:: console

    $ pysynth --demo anthem --output pysynth_anthem.wav

Pick a sound at the command line:

.. code-block:: console

    $ pysynth --song "4c4 4e4 4g4 2c5" --sound e --output epiano.wav

Render an ABC or MIDI file:

.. code-block:: console

    $ pysynth render tune.abc --sound piano --output tune.wav
    $ pysynth render tune.mid --track 1 --sound e --output tune.wav

Compare a short phrase across multiple sounds:

.. code-block:: console

    $ pysynth preview --sound a --sound b --sound e

Or keep the sound/progress defaults in ``pysynth.json``:

.. code-block:: json

    {
      "sound": "b",
      "progress": {
        "enabled": true,
        "small_threshold": 12,
        "max_updates": 6,
        "show_time": false
      },
      "sample_path": "/path/to/48khz24bit"
    }

Supported sound values are ``a``, ``b``, ``c``, ``d``, ``e``, ``p``, ``s``,
``samp``, and ``beeper``. Progress can also be controlled with
``--progress-every``, ``--progress-percent``, ``--progress-max-updates``, and
``--progress-small-threshold``. Use ``pysynth list-sounds`` to see sound
descriptions and aliases, and ``pysynth config init`` to create a starter
config file.

To use *pysynth*:

.. code-block:: console

    $ python -m tomita.legacy.pysynth

To use *pysynth_b*:

.. code-block:: console

    $ python -m tomita.legacy.pysynth_b

To use *pysynth_c*:

.. code-block:: console

    $ python -m tomita.legacy.pysynth_c

and so on.

License
-------

`GNU General Public License v3.0 <https://choosealicense.com/licenses/gpl-3.0/>`_


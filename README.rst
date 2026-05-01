===============
PySynth Unified
===============

.. image:: https://img.shields.io/pypi/v/tomita.svg
        :target: https://pypi.python.org/pypi/tomita

.. image:: https://img.shields.io/travis/python-g4brielvs/tomita.svg
        :target: https://travis-ci.com/g4brielvs/python-tomita

.. image:: https://pyup.io/repos/github/g4brielvs/python-tomita/shield.svg
     :target: https://pyup.io/repos/github/g4brielvs/python-tomita
     :alt: Updates

.. image:: https://readthedocs.org/projects/tomita/badge/?version=latest
        :target: https://tomita.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://img.shields.io/pypi/l/Tomita.svg
        :target: https://pypi.python.org/pypi/tomita/
        :alt: License

*PySynth Unified* is a command-line music and synthesizer package based on the
maintained ``g4brielvs/python-tomita`` fork of PySynth. It keeps the Tomita
package namespace for compatibility and also exposes a ``pysynth`` command and
Python facade.

* Free software: GNU General Public License v3
* Documentation: https://tomita.readthedocs.io.

About
-----

Isao Tomita (冨田 勲, Tomita Isao, 22 April 1932 – 5 May 2016), also known mononymically 
as Tomita, was a Japanese music-composer, regarded as one of the pioneers of electronic 
music and space music,and as one of the most famous producers of analog synthesizer 
arrangements. `Wikipedia <https://en.wikipedia.org/wiki/Isao_Tomita>`_


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

PySynth
-------

All scripts from *PySynth* can be found as modules.

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


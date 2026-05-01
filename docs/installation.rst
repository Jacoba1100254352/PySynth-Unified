============
Installation
============

Command-line install
--------------------

On macOS with Homebrew Python, install PySynth Unified with ``pipx``. This
keeps the command-line app in its own virtual environment and avoids Python's
``externally-managed-environment`` restriction:

.. code-block:: console

    $ brew install pipx
    $ pipx ensurepath
    $ export PATH="$HOME/.local/bin:$PATH"
    $ pipx install "git+https://github.com/Jacoba1100254352/PySynth-Unified.git"
    $ pysynth list-sounds

The ``export`` line only affects the terminal you already have open. Opening a
new terminal after ``pipx ensurepath`` works too.

If you previously installed this repository while pipx reported
``installed package tomita 0.2.0``, replace that older pipx environment once:

.. code-block:: console

    $ pipx uninstall tomita
    $ pipx install "git+https://github.com/Jacoba1100254352/PySynth-Unified.git"


From sources
------------

For the older clone-and-install workflow, use ``make install`` from the repo
root. It creates a local ``.venv`` and installs the package there instead of
writing into system Python:

.. code-block:: console

    $ git clone https://github.com/Jacoba1100254352/PySynth-Unified.git
    $ cd PySynth-Unified
    $ make install
    $ .venv/bin/pysynth list-sounds

For development, activate a virtual environment and install normally:

.. code-block:: console

    $ python -m venv .venv
    $ . .venv/bin/activate
    $ python -m pip install -U pip
    $ python -m pip install -e .

Avoid ``python setup.py install``; modern pip installs handle dependencies and
console scripts more reliably.

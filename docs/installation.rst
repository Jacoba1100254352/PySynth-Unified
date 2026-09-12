============
Installation
============

Python and platform compatibility
---------------------------------

The release suite tests CPython 3.9 through 3.14 on Linux and Python 3.14 on
macOS and Windows. Python 3.9 is retained for legacy compatibility; it
`reached upstream end of life <https://peps.python.org/pep-0596/>`_ in October
2025. Prefer a maintained Python version for new installations. Newer Python
versions are not claimed as tested until they enter the release matrix.

Release artifacts
-----------------

Download the wheel or source archive and ``SHA256SUMS`` from `GitHub Releases
<https://github.com/Jacoba1100254352/PySynth-Unified/releases>`_. In an
activated virtual environment, install the downloaded wheel::

    python -m pip install pysynth_unified-0.3.1-py3-none-any.whl

On Windows, create the environment with ``py -m venv .venv`` and activate it
in PowerShell with ``.venv\Scripts\Activate.ps1``. Alternatively, call
``.venv\Scripts\python.exe -m pip install <wheel-path>`` without activation.
The source archive installs with the same command, substituting its
``.tar.gz`` filename. Both install the ``pysynth`` and ``tomita`` commands.

Git installation commands below follow development. Append ``@v0.3.1`` to the
Git URL to install the verified release. A GitHub release does not imply a
PyPI publication.

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


Python projects and VS Code
---------------------------

``pipx`` is intended for the command-line app. For code that imports
``pysynth``, create a virtual environment inside the project and install the
package there:

.. code-block:: console

    $ python3 -m venv .venv
    $ . .venv/bin/activate
    $ python -m pip install -U pip
    $ python -m pip install "git+https://github.com/Jacoba1100254352/PySynth-Unified.git"

Configure the editor to use that ``.venv`` interpreter. This keeps imports,
the terminal command, and the editor on the same installation.


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
    $ python -m pip install -e '.[dev]'

Avoid ``python setup.py install``; modern pip installs handle dependencies and
console scripts more reliably.

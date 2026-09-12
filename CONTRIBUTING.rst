.. highlight:: shell

============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

This fork does not currently have GitHub Issues enabled. A focused pull
request containing a minimal reproduction or failing regression test is the
most direct way to report a defect.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Check open pull requests and the maintained upstream before starting work, and
include a regression test with each fix.

Implement Features
~~~~~~~~~~~~~~~~~~

Keep additions compatible with the legacy entrypoints and route shared
behavior through ``tomita.synth`` and ``tomita.progress``.

Write Documentation
~~~~~~~~~~~~~~~~~~~

PySynth Unified could always use more documentation, whether as part of the
project docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

If you are proposing a feature in a pull request:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up PySynth Unified for local development.

1. Fork the `PySynth-Unified` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/PySynth-Unified.git

3. Install your local copy into a virtual environment::

    $ cd PySynth-Unified/
    $ make install-editable
    $ . .venv/bin/activate

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, run the maintained checks. Tox also tests
   any supported Python versions installed on your machine::

    $ make lint
    $ make test
    $ make docs
    $ make dist
    $ make test-all

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 3.9 and newer.

Tips
----

To run a subset of tests::

$ python -m pytest tests/test_tomita.py


Releasing
---------

Release commits, tags, and uploaded artifacts are separate checkpoints. Start
from a clean checkout. Update the version in ``setup.py``, ``setup.cfg``, and
``tomita/__init__.py`` together, update versioned installation examples, and
write ``HISTORY.rst`` and ``RELEASE_NOTES.md``. Validate the proposed release::

    $ make lint
    $ make test
    $ make docs
    $ make release-check

The normal (non-prerelease) 0.x release benchmark requires all of the following:

* Passing installed-package tests for CPython 3.9--3.14 on Linux and 3.14 on
  macOS and Windows. A local tox skip is not evidence for a missing version.
* Passing lint, compilation, strict Sphinx builds, package metadata checks,
  and clean installs of both wheel and source archive. ``release-check`` runs
  on Python 3.14 with the development extras installed, checks archive
  contents, runs the compatibility suite outside the source checkout, builds
  documentation from the source archive, and then writes ``SHA256SUMS``.
* Consistent version metadata and release notes, a reviewed staged diff,
  redacted secret scanning, and documented compatibility limits.
* A passing hosted workflow for the exact release commit. Build the final
  artifacts from that commit, create the matching ``vX.Y.Z`` tag, publish
  those verified artifacts and checksums on GitHub, then download them again
  and verify the checksums and tag target.

If a required gate is incomplete, fix it before publishing a normal release;
use a clearly labeled prerelease only for an intentional provisional milestone.
The project remains pre-1.0: this benchmark verifies the documented rendering
surface, not full MIDI/ABC conformance, interactive audio playback, or every
external sample library. ``make release`` only prepares and verifies artifacts.
Publishing to PyPI is a separate, explicitly configured distribution step.

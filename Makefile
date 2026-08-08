.PHONY: clean clean-test clean-pyc clean-build coverage dist docs help install install-active install-editable install-user lint open-docs release servedocs test test-all venv
.DEFAULT_GOAL := help
PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV_PYTHON) -m pip

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := $(VENV_PYTHON) -c "$$BROWSER_PYSCRIPT"

help:
	@$(PYTHON) -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

lint: ## check style with flake8
	$(VENV_PYTHON) -m flake8 tomita pysynth tests

test: ## run tests quickly with the default Python
	$(VENV_PYTHON) -m pytest -q

test-all: ## run tests on every Python version with tox
	$(VENV_PYTHON) -m tox

coverage: ## check code coverage quickly with the default Python
	$(VENV_PYTHON) -m coverage run --source tomita,pysynth -m pytest
	$(VENV_PYTHON) -m coverage report -m
	$(VENV_PYTHON) -m coverage html
	$(BROWSER) htmlcov/index.html

docs: ## generate Sphinx HTML documentation, including API docs
	$(VENV_PYTHON) -m sphinx -W --keep-going -b html docs docs/_build/html

open-docs: docs ## build and open the Sphinx HTML documentation
	$(BROWSER) docs/_build/html/index.html

servedocs: docs ## compile the docs watching for changes
	$(VENV)/bin/watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: dist ## package and upload a release
	$(VENV_PYTHON) -m twine upload dist/*

dist: ## build and validate source and wheel packages
	$(MAKE) clean-build
	$(VENV_PYTHON) -m build
	$(VENV_PYTHON) -m twine check dist/*
	ls -l dist

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install -U pip

venv: $(VENV_PYTHON) ## create a local virtual environment

clean-legacy-install: ## remove stale local metadata from pre-0.3 installs
	rm -fr *.egg-info
	rm -fr $(VENV)/lib/python*/site-packages/tomita
	rm -fr $(VENV)/lib/python*/site-packages/pysynth
	rm -fr $(VENV)/lib/python*/site-packages/tomita-*.dist-info
	rm -f $(VENV)/lib/python*/site-packages/__editable__.tomita-*.pth
	rm -f $(VENV)/lib/python*/site-packages/__editable___tomita_*_finder.py
	rm -f $(VENV)/lib/python*/site-packages/pysynth_unified_editable.pth

install: venv clean-legacy-install ## install the package into a local .venv
	$(VENV_PIP) install .
	@echo "Installed. Run: $(VENV)/bin/pysynth list-sounds"

install-active: ## install the package into the active Python environment
	$(PIP) install .

install-user: ## install the package into the user site-packages
	$(PIP) install --user .

install-editable: venv clean-legacy-install ## install the package in editable/development mode
	$(VENV_PIP) install -e '.[dev]'
	site="$$( $(VENV_PYTHON) -c 'import site; print(site.getsitepackages()[0])' )" && printf '%s\n' '$(CURDIR)' > "$$site/pysynth_unified_editable.pth"
	@echo "Installed editable. Run: $(VENV)/bin/pysynth list-sounds"

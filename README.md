# pyven
Manage development of multiple Python projects

## Install
These are generic installation instructions.

### To use, permanently
The quickest way to get started is to install the current release from PyPI:
```
pip3 install --user pyven
```

### To use, temporarily
If you prefer to keep .local clean, install to a virtualenv:
```
python3 -m venv venvname
venvname/bin/pip install pyven
. venvname/bin/activate
```

### To develop
First clone the repo using HTTP or SSH:
```
git clone https://github.com/combatopera/pyven.git
git clone git@github.com:combatopera/pyven.git
```
Now use pyven's pipify to create a setup.py, which pip can then use to install the project editably:
```
python3 -m venv pyvenvenv
pyvenvenv/bin/pip install pyven
pyvenvenv/bin/pipify pyven

python3 -m venv venvname
venvname/bin/pip install -e pyven
. venvname/bin/activate
```

## Commands

### drmake
Build a Docker image with automatic tag.

### gclean
Remove files matching patterns below #glean in .gitignore file.

### initopt
Furnish the venv with editable projects and their dependencies, with mccs solver support.

### launch
Run project using a suitable venv from the pool.

### minreqs
Print project.arid snippet pinning requires to their minimum allowed versions.

### pipify
Generate setuptools files for a project.arid project.

### release
Release project to PyPI, with manylinux wheels as needed.

### tasks
Show all XXX/TODO/FIXME comments in project.

### tests
Run project unit tests and more, also suitable for CI.

### tryinstall
Check last release can be installed from PyPI and its tests still pass, for use by CI.

# venvpool
Run your Python scripts using an automated pool of virtual environments to satisfy their requirements

## Install
<!--
These are generic installation instructions.
-->
The activate script is a single file with no requirements of its own other than Python 2 or 3.

<!--
### To use, permanently
The quickest way to get started is to install the current release from PyPI:
```
pip3 install --user venvpool
```

### To use, temporarily
If you prefer to keep .local clean, install to a virtualenv:
```
python3 -m venv venvname
venvname/bin/pip install venvpool
. venvname/bin/activate
```
-->
### To use
Download the latest activate script into your personal scripts directory:
```
cd ~/.local/bin
wget https://raw.githubusercontent.com/combatopera/venvpool/trunk/activate
chmod +x activate
```

### To develop
First clone the repo using HTTP or SSH:
```
git clone https://github.com/combatopera/venvpool.git
git clone git@github.com:combatopera/venvpool.git
```
<!--
Now use pyven's pipify to create a setup.py, which pip can then use to install the project editably:
```
python3 -m venv pyvenvenv
pyvenvenv/bin/pip install pyven
pyvenvenv/bin/pipify venvpool

python3 -m venv venvname
venvname/bin/pip install -e venvpool
. venvname/bin/activate
```
-->
Now symlink the activate script:
```
ln -s "$PWD/venvpool/activate" ~/.local/bin/
```

## Commands

### motivate
Create and maintain wrapper scripts in ~/.local/bin for all runnable modules in the given projects, or the current project if none given.

### motivate -S
Create/maintain wrappers for all console_scripts of the given requirement specifier.

### motivate -C
Compact the pool of venvs.

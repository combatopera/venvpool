# Copyright 2013, 2014, 2015, 2016, 2017, 2020, 2022, 2023 Andrzej Cichocki

# This file is part of venvpool.
#
# venvpool is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# venvpool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with venvpool.  If not, see <http://www.gnu.org/licenses/>.

'Create and maintain wrapper scripts in ~/.local/bin for all runnable modules in the given projects, or the current project if none given.'
from . import main

if '__main__' == __name__:
    main()

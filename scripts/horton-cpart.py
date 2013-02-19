#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Horton is a Density Functional Theory program.
# Copyright (C) 2011-2012 Toon Verstraelen <Toon.Verstraelen@UGent.be>
#
# This file is part of Horton.
#
# Horton is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# Horton is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
#--

import sys, argparse

import h5py as h5
from horton import System, cpart_schemes, Cell, ProAtomDB

def parse_args():
    parser = argparse.ArgumentParser(prog='horton-copart.py',
        description='Partition the density in a cube file.')

    parser.add_argument('cube',
        help='The cube file.')
    parser.add_argument('scheme', choices=cpart_schemes.keys(),
        help='The scheme to be used for the partitioning')
    parser.add_argument('atoms',
        help='An HDF5 file with atomic reference densities.')
    parser.add_argument('--smooth', '-s', default=False, action='store_true',
        help='Use this option when no special measures are needed to integrate '
             'the cusps accurately.')
    parser.add_argument('--reduce', '-r', default=1, type=int,
        help='Reduce the grid by subsamping with the given stride in all three '
             'directions. Zero and negative values are ignored.')

    # TODO: add argument for periodic boundary conditions
    # TODO: add argument to chop of last slice(s)

    return parser.parse_args()


def main():
    args = parse_args()

    # Load the system
    sys = System.from_file(args.cube)
    ui_grid = sys.props['ui_grid']
    moldens = sys.props['cube_data']

    # Reduce the grid if required
    if args.reduce > 1:
        if (ui_grid.shape % args.reduce != 0).any():
            raise ValueError('The stride is not commensurate with all three grid demsions.')

        ui_grid.shape /= args.reduce
        moldens = moldens[::args.reduce, ::args.reduce, ::args.reduce].copy()
        rvecs = ui_grid.grid_cell.rvecs*args.reduce
        ui_grid.grid_cell = Cell(rvecs)

    # Load the proatomdb
    proatomdb = ProAtomDB.from_file(args.atoms)

    # Run the partitioning
    cpart = cpart_schemes[args.scheme](sys, ui_grid, moldens, proatomdb, args.smooth)
    cpart.do_charges()
    cpart.do_dipoles()
    cpart.do_volumes()

    # Store the results in an HDF5 file
    with h5.File(args.cube + '.h5') as f:
        folder = '%s_r%i' % (args.scheme, args.reduce)
        if args.smooth:
            folder += '_s'
        if folder in f:
            del f[folder]
        grp = f.create_group(folder)
        grp['charges'] = cpart['charges']
        grp['dipoles'] = cpart['dipoles']
        grp['volumes'] = cpart['volumes']


if __name__ == '__main__':
    main()
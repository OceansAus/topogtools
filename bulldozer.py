#!/usr/bin/env python

import sys
import os
import time
import shutil
import numpy as np
import argparse
import netCDF4 as nc

"""
Apply some topography/bathymetry changes based on a 'changes' log.

* Does various checks such as not creating holes.
* Updates netcdf history attribute.

The input is taken from stdin. The format of the input is a list of
comma-separated line with the following values:

'i index', 'j index', 'original depth', 'new depth'

For example to run on a single point:

echo -e "112, 246, 0.0, 50.0" | ./bulldozer.py test/topog.nc

To run a whole file:

cat file.csv | ./bulldozer.py test/topog.nc

Where the contents of file could look something like this:

112, 246, 0.0, 50.0
113, 246, 0.0, 50.0
"""

def making_a_hole(i, j, new_depth, depth_var):

    # Check that we are not creating a hole
    num_neighbours = 0
    num_neighbours_shallower = 0
    if i-1 > 0:
        num_neighbours += 1
        if depth_var[j, i-1] > new_depth:
            num_neighbours_shallower += 1

    if j+1 < depth_var.shape[1]:
        num_neighbours += 1
        if depth_var[j+1, i] > new_depth:
            num_neighbours_shallower += 1

    if i+1 < depth_var.shape[0]:
        num_neighbours += 1
        if depth_var[j, i+1] > new_depth:
            num_neighbours_shallower += 1

    if j-1 > 0:
        num_neighbours += 1
        if depth_var[j-1, i] > new_depth:
            num_neighbours_shallower += 1

    if num_neighbours == num_neighbours_shallower:
        return True
    else:
        return False


def apply_change(i, j, orig_depth, new_depth, depth_var, force=False):
    errstr = None

    # Check that the original depths match
    if depth_var[j, i] != orig_depth:
        errstr = 'Got {}, expected {} depth'.format(depth_var[j, i], orig_depth)

    # See whether we're making a hole
    if making_a_hole(i, j, new_depth, depth_var):
        errstr = 'Made a hole'

    if force or errstr is None:
        depth_var[j, i] = new_depth

    return errstr

def bulldoze(new_topog, force=False):

    err = False
    with nc.Dataset(new_topog, 'r+') as nf:
        depth = nf.variables['depth']

        for line in sys.stdin.readlines():
            try:
                l = line.split(',')
                i = int(l[0].strip())
                j = int(l[1].strip())
                orig_depth = float(l[2].strip())
                new_depth = float(l[3].strip())
            except (ValueError, IndexError):
                print('Error: {} bad stdin input format')
                err = True
                break

            errstr = apply_change(i, j, orig_depth, new_depth, depth,
                                  force=force)
            if errstr is not None:
                errstr = errstr + ' at {} {}'.format(l[0], l[1])
                if force:
                    print('Warning: ' + errstr, file=sys.stderr)
                else:
                    print('Error: ' + errstr, file=sys.stderr)
                    err = True
                    break

            # Add to history attribute
            hist_str = time.ctime(time.time()) + ' : echo ' + \
                        line.strip() + ' | ' + ' '.join(sys.argv)
            if 'history' not in nf.ncattrs():
                nf.history = hist_str
            else:
                nf.history = nf.history + " " + hist_str

    return err

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('orig_topog', help='The topog file to be changed.')
    parser.add_argument('new_topog',  help='The new topog file.')
    parser.add_argument('--force', default=False,
                        help="Force changes, don't exit on a bad change.")

    args = parser.parse_args()

    # Check that files exist
    if os.path.exists(args.new_topog):
        print('Error: {} already exists'.format(args.new_topog),
              file=sys.stderr)
        parser.print_help()
        return 1
    # Make new_topog
    shutil.copyfile(args.orig_topog, args.new_topog)
    new_topog = args.new_topog

    if not os.path.exists(args.orig_topog):
        print('Error: {} not found'.format(args.orig_topog), file=sys.stderr)
        parser.print_help()
        return 1

    err = bulldoze(args.new_topog, args.force)
    if err and args.new_topog is not None:
        os.remove(args.new_topog)
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())

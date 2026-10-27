#!/usr/bin/env python3
"""Combine single-tag WRF-WVTs mask files into one multi-tag trmask_d01.

Each input file holds a TRMASK (1 = source, 0 = elsewhere) on the same grid.
Tag 1 is written as TRMASK, tag 2 as TRMASK_T2, tag 3 as TRMASK_T3, ...
WRF reads the file at the start time of a cold-start run, so the file's
Times must equal start_date (--start).

    python3 make_trmask_multitag.py --start 1980-04-01_00:00:00 -o trmask_d01 \
        trmask_npac.nc trmask_gulf.nc trmask_land.nc

A 3D source (TRMASK3D) or sink (TRMASK3D2) in an input file is copied the same
way (TRMASK3D_T2, TRMASK3D2_T2, ...).
"""
import argparse
import shutil

import netCDF4
import numpy as np

MASKS = ('TRMASK', 'TRMASK3D', 'TRMASK3D2')


def tagname(name, t):
    return name if t == 1 else '%s_T%d' % (name, t)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('masks', nargs='+', help='single-tag mask files, in tag order')
    ap.add_argument('-o', '--output', default='trmask_d01')
    ap.add_argument('--start', required=True, help='run start time, YYYY-MM-DD_HH:MM:SS')
    a = ap.parse_args()

    shutil.copy(a.masks[0], a.output)
    with netCDF4.Dataset(a.output, 'a') as out:
        for t, path in enumerate(a.masks, start=1):
            with netCDF4.Dataset(path) as src:
                found = [m for m in MASKS if m in src.variables]
                if not found:
                    raise SystemExit('%s has none of %s' % (path, MASKS))
                for m in found:
                    s = src[m]
                    name = tagname(m, t)
                    if name not in out.variables:
                        v = out.createVariable(name, 'f4', s.dimensions)
                        for att in s.ncattrs():
                            v.setncattr(att, s.getncattr(att))
                    else:
                        v = out[name]
                    if s.shape != v.shape:
                        raise SystemExit('%s: %s has shape %s, expected %s' % (path, m, s.shape, v.shape))
                    v[:] = (np.asarray(s[:]) > 0.).astype('f4')
                    v.description = 'tag %d %s from %s' % (t, m, path)
                    print('tag %2d  %-14s <- %s  (%d source points)' % (t, name, path, int((np.asarray(s[:]) > 0).sum())))
        out['Times'][0] = netCDF4.stringtochar(np.array([a.start], 'S19'))
    n = len(a.masks)
    print('wrote %s: %d tags -> set tracer_opt = %s in namelist.input' % (a.output, n, 4 if n == 1 else 40 + n))


if __name__ == '__main__':
    main()

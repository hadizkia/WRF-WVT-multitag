#!/usr/bin/env python3
"""Tracer-mask files for the multi-tag WVT tests (regions small domain).

    trmask_A        TRMASK = Local Land (LL)                    single tag
    trmask_B        TRMASK = not LL                             single tag
    trmask_AA       TRMASK = LL,  TRMASK_T2 = LL                two tags, identical
    trmask_AB       TRMASK = LL,  TRMASK_T2 = not LL            two tags, complementary
"""
import shutil
import sys

import netCDF4
import numpy as np

src = sys.argv[1]           # production LL mask: trmask/trmask_d01_LL
out = sys.argv[2] if len(sys.argv) > 2 else '.'
start = sys.argv[3] if len(sys.argv) > 3 else '1980-04-01_00:00:00'   # WRF reads the mask at the start time


def write(name, masks):
    dst = '%s/%s' % (out, name)
    shutil.copy(src, dst)
    with netCDF4.Dataset(dst, 'a') as nc:
        ll = nc['TRMASK']
        for var, val in masks.items():
            v = nc[var] if var in nc.variables else nc.createVariable(var, 'f4', ll.dimensions)
            for att in ('FieldType', 'MemoryOrder', 'units', 'stagger'):
                if att in ll.ncattrs() and att not in v.ncattrs():
                    v.setncattr(att, ll.getncattr(att))
            v.description = var
            v[:] = val
        nc['Times'][0] = netCDF4.stringtochar(np.array([start], 'S19'))
    print(dst, {k: float(np.asarray(v).sum()) for k, v in masks.items()})


with netCDF4.Dataset(src) as nc:
    ll = np.asarray(nc['TRMASK'][:]) > 0.
a = ll.astype('f4')
b = (~ll).astype('f4')
write('trmask_A', {'TRMASK': a})
write('trmask_B', {'TRMASK': b})
write('trmask_AA', {'TRMASK': a, 'TRMASK_T2': a})
write('trmask_AB', {'TRMASK': a, 'TRMASK_T2': b})

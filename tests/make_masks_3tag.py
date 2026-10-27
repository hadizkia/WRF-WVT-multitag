#!/usr/bin/env python3
"""Masks for the 3-tag test on the original full domain (940 x 420).

    trmask_npac   TRMASK = North Pacific (oceanL)                   single tag
    trmask_gom    TRMASK = Gulf of Mexico / Atlantic (gulf)         single tag
    trmask_ll     TRMASK = Local Land (LL)                          single tag
    trmask_3tag   TRMASK = npac, TRMASK_T2 = gom, TRMASK_T3 = ll    three tags
"""
import shutil
import sys

import netCDF4
import numpy as np

src_dir, out = sys.argv[1], sys.argv[2]          # trmask/orig_bigdomain, output dir
start = sys.argv[3] if len(sys.argv) > 3 else '1980-04-01_00:00:00'   # WRF reads the mask at the start time
SRC = {'npac': 'trmask_d01_oceanL', 'gom': 'trmask_d01_gulf', 'll': 'trmask_d01_LL'}

masks = {}
for k, f in SRC.items():
    with netCDF4.Dataset('%s/%s' % (src_dir, f)) as nc:
        masks[k] = (np.asarray(nc['TRMASK'][:]) > 0.).astype('f4')


def write(name, fields):
    dst = '%s/%s' % (out, name)
    shutil.copy('%s/%s' % (src_dir, SRC['ll']), dst)
    with netCDF4.Dataset(dst, 'a') as nc:
        ref = nc['TRMASK']
        for var, val in fields.items():
            v = nc[var] if var in nc.variables else nc.createVariable(var, 'f4', ref.dimensions)
            for att in ('FieldType', 'MemoryOrder', 'units', 'stagger'):
                if att in ref.ncattrs() and att not in v.ncattrs():
                    v.setncattr(att, ref.getncattr(att))
            v.description = var
            v[:] = val
        nc['Times'][0] = netCDF4.stringtochar(np.array([start], 'S19'))
    print(dst, {k: int(v.sum()) for k, v in fields.items()})


write('trmask_npac', {'TRMASK': masks['npac']})
write('trmask_gom', {'TRMASK': masks['gom']})
write('trmask_ll', {'TRMASK': masks['ll']})
write('trmask_3tag', {'TRMASK': masks['npac'], 'TRMASK_T2': masks['gom'], 'TRMASK_T3': masks['ll']})

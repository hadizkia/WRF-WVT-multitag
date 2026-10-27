#!/usr/bin/env python3
"""3-tag run vs the three single-tag production WRF-WVT runs (see run_test3.sh)."""
import glob
import sys

import netCDF4
import numpy as np

T = sys.argv[1]
TAG = ['qv_tr', 'qc_tr', 'qr_tr', 'qi_tr', 'qs_tr', 'qg_tr', 'TR_RAINNC', 'TR_RAINC', 'TR_SNOWNC',
       'TR_GRAUPELNC', 'TRQFX', 'TR_THUM_U_PHY_DT', 'TR_THUM_V_PHY_DT']
MODEL = ['U', 'V', 'W', 'T', 'PH', 'MU', 'P', 'QVAPOR', 'QCLOUD', 'QRAIN', 'QICE', 'QSNOW', 'QGRAUP',
         'RAINNC', 'RAINC', 'PSFC', 'T2', 'Q2', 'HFX', 'QFX', 'LH', 'PBLH', 'TSK', 'SMOIS']


def tagname(v, t):          # generator naming rule
    return v if t == 1 else v + ('_T%d' % t if v.isupper() else '_t%d' % t)


def last(run):
    f = sorted(glob.glob('%s/runs/%s/wrfout/wrfout_d01_*' % (T, run)))
    return netCDF4.Dataset(f[-1]) if f else None


def diff(a, va, b, vb):
    if a is None or b is None:
        return 'run missing'
    if va not in a.variables or vb not in b.variables:
        return 'variable missing'
    x = np.asarray(a[va][-1], 'f8'); y = np.asarray(b[vb][-1], 'f8')
    d = np.abs(x - y).max()
    return '%.3e   (max |field| %.3e)' % (d, np.abs(y).max())


R = {r: last(r) for r in ('npac', 'gom', 'll', 'tag3')}
for r, nc in R.items():
    print('%-5s %s' % (r, 'none' if nc is None else '%s  %s' % (nc.filepath(), netCDF4.chartostring(nc['Times'][-1]))))

print('\n== model fields: 3-tag run vs single-tag npac run (must be identical)')
for v in MODEL:
    print('   %-8s %s' % (v, diff(R['tag3'], v, R['npac'], v)))
print('\n== single-tag runs agree with each other on the model fields (sanity)')
for v in ('T', 'QVAPOR', 'RAINNC'):
    print('   %-8s gom-npac %s | ll-npac %s' % (v, diff(R['gom'], v, R['npac'], v), diff(R['ll'], v, R['npac'], v)))
for t, run in ((1, 'npac'), (2, 'gom'), (3, 'll')):
    print('\n== tag %d (%s) of the 3-tag run vs single-tag %s run' % (t, run, run))
    for v in TAG:
        print('   %-22s vs %-18s %s' % (tagname(v, t), v, diff(R['tag3'], tagname(v, t), R[run], v)))

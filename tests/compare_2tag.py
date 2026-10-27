#!/usr/bin/env python3
"""Compare the multi-tag WVT test runs (see run_tests.sh); max |difference| per check."""
import glob
import sys

import netCDF4
import numpy as np

T = sys.argv[1]
TAG1 = ['qv_tr', 'qc_tr', 'qr_tr', 'qi_tr', 'qs_tr', 'qg_tr', 'TR_RAINNC', 'TR_RAINC', 'TR_SNOWNC',
        'TR_GRAUPELNC', 'TRQFX', 'TR_THUM_U_PHY_DT', 'TR_THUM_V_PHY_DT']
TAG2 = {v: v + ('_T2' if v.isupper() else '_t2') for v in TAG1}   # generator naming rule
MODEL = ['U', 'V', 'W', 'T', 'PH', 'MU', 'P', 'QVAPOR', 'QCLOUD', 'QRAIN', 'QICE', 'QSNOW', 'QGRAUP',
         'RAINNC', 'RAINC', 'PSFC', 'T2', 'Q2', 'HFX', 'QFX', 'LH', 'PBLH', 'TSK', 'SMOIS']


def last(run):
    f = sorted(glob.glob('%s/runs/%s/wrfout/wrfout_d01_*' % (T, run)))
    return netCDF4.Dataset(f[-1]) if f else None


def diff(a, va, b, vb):
    if va not in a.variables or vb not in b.variables:
        return 'missing'
    x = np.asarray(a[va][-1], dtype='f8'); y = np.asarray(b[vb][-1], dtype='f8')
    d = np.abs(x - y).max()
    scale = max(np.abs(x).max(), 1e-30)
    return '%.3e (rel %.1e)' % (d, d / scale)


runs = {r: last(r) for r in ('A_prod', 'A_new', 'AA', 'AB', 'B_prod')}
for r, nc in runs.items():
    print(r, 'output:', 'none' if nc is None else nc.filepath(), '' if nc is None else str(netCDF4.chartostring(nc['Times'][-1])))


def block(title, a, b, pairs):
    print('\n== ' + title)
    if runs[a] is None or runs[b] is None:
        print('   (run missing)'); return
    for va, vb in pairs:
        print('   %-22s %-22s %s' % (va, vb, diff(runs[a], va, runs[b], vb)))


block('1. A_new vs A_prod, model fields (tracer_opt=4 must be bit-identical)', 'A_new', 'A_prod', [(v, v) for v in MODEL])
block('1. A_new vs A_prod, tag 1', 'A_new', 'A_prod', [(v, v) for v in TAG1])
block('2. AA vs A_prod, model fields (extra tag must not touch the model)', 'AA', 'A_prod', [(v, v) for v in MODEL])
block('2. AA vs A_prod, tag 1', 'AA', 'A_prod', [(v, v) for v in TAG1])
block('2. AA tag 2 vs AA tag 1 (identical masks)', 'AA', 'AA', [(TAG2[v], v) for v in TAG1])
block('3. AB vs A_prod, model fields', 'AB', 'A_prod', [(v, v) for v in MODEL])
block('3. AB tag 1 vs A_prod tag 1', 'AB', 'A_prod', [(v, v) for v in TAG1])
block('3. AB tag 2 vs B_prod tag 1 (each tag = its own single-tag run)', 'AB', 'B_prod', [(TAG2[v], v) for v in TAG1])

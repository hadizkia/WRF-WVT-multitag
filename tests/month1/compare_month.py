#!/usr/bin/env python3
"""July 1980: the 3-tag WRF-WVT run vs the three single-tag WRF-WVT runs (see run.sh).

    tag 1 = North Pacific (npac), tag 2 = Gulf of Mexico (gom), tag 3 = Local Land (ll)

Writes, in the month1 directory:
    compare_report.txt   max |difference| over all 32 daily outputs, every field
    compare_july1980.png maps of July tagged precipitation (single | 3-tag | difference)
                         + daily SWNA-mean tagged precipitation, single vs 3-tag
NaN (WRF-WVTs puts NaN in qv_tr inside the boundary zone) counts as equal only if both runs
have NaN in the same cell.
"""
import glob
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import netCDF4
import numpy as np

M = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
TAG = ['qv_tr', 'qc_tr', 'qr_tr', 'qi_tr', 'qs_tr', 'qg_tr', 'TR_RAINNC', 'TR_RAINC', 'TR_SNOWNC',
       'TR_GRAUPELNC', 'TRQFX', 'TR_THUM_U_PHY_DT', 'TR_THUM_V_PHY_DT']
MODEL = ['U', 'V', 'W', 'T', 'PH', 'MU', 'P', 'QVAPOR', 'QCLOUD', 'QRAIN', 'QICE', 'QSNOW', 'QGRAUP',
         'RAINNC', 'RAINC', 'PSFC', 'T2', 'Q2', 'HFX', 'QFX', 'LH', 'PBLH', 'TSK', 'SMOIS']
SINGLE = [(1, 'npac', 'North Pacific'), (2, 'gom', 'Gulf of Mexico'), (3, 'll', 'Local Land')]
COLOR = {'npac': '#2a78d6', 'gom': '#eb6834', 'll': '#1baf7a'}


def tagname(v, t):          # multi-tag naming rule: tag 1 unchanged, tag k adds _t<k> / _T<k>
    return v if t == 1 else v + ('_T%d' % t if v.isupper() else '_t%d' % t)


files = {r: sorted(glob.glob('%s/runs/%s/wrfout/wrfout_d01_*' % (M, r))) for r in ('npac', 'gom', 'll', 'tag3')}
n = min(len(f) for f in files.values())
assert n > 0, {r: len(f) for r, f in files.items()}
dates = [os.path.basename(f)[11:21] for f in files['tag3'][:n]]


def maxdiff(x, y):
    x = np.asarray(x, 'f8'); y = np.asarray(y, 'f8')
    nx, ny = np.isnan(x), np.isnan(y)
    if (nx != ny).any():
        return np.inf, np.nan
    ok = ~nx
    yi = y[..., 5:-5, 5:-5]               # field size reported for the interior (WRF-WVTs boundary-zone artefacts)
    return (np.abs(x[ok] - y[ok]).max() if ok.any() else 0.), float(np.nanmax(np.abs(yi)))


# ---- 1. every field, every day
checks = [('model fields: 3-tag vs single-tag npac', 'tag3', 'npac', [(v, v) for v in MODEL]),
          ('model fields: single-tag gom vs npac (sanity)', 'gom', 'npac', [(v, v) for v in MODEL]),
          ('model fields: single-tag ll vs npac (sanity)', 'll', 'npac', [(v, v) for v in MODEL])]
for t, r, lab in SINGLE:
    checks.append(('tag %d (%s) of 3-tag run vs single-tag %s run' % (t, lab, r), 'tag3', r,
                   [(tagname(v, t), v) for v in TAG]))
res = {}
for i in range(n):
    nc = {r: netCDF4.Dataset(files[r][i]) for r in files}
    for title, a, b, pairs in checks:
        for va, vb in pairs:
            d, s = maxdiff(nc[a][va][0], nc[b][vb][0])
            k = (title, va, vb)
            p = res.get(k, (0., 0.))
            res[k] = (max(p[0], d), max(p[1], s if np.isfinite(s) else 0.))
    for x in nc.values():
        x.close()
    print('compared', dates[i], flush=True)

lines = ['3-tag WRF-WVT vs single-tag WRF-WVT, 941 x 421 domain, %s .. %s, %d daily outputs' % (dates[0], dates[-1], n),
         'max |difference| over every grid cell (incl. boundary zone), level and output time  (inf = NaN pattern differs)',
         'max|field| = largest |value| in the interior (5-cell boundary zone excluded), for scale', '']
allzero = True
for title, a, b, pairs in checks:
    lines.append('== ' + title)
    for va, vb in pairs:
        d, s = res[(title, va, vb)]
        allzero &= (d == 0.)
        lines.append('   %-20s vs %-18s max|diff| = %-10.3e  (max|field| = %.3e)' % (va, vb, d, s))
    lines.append('')
lines.append('RESULT: %s' % ('ALL FIELDS BIT-FOR-BIT IDENTICAL' if allzero else 'DIFFERENCES FOUND'))

# ---- 2. July precipitation + SWNA recycling-style numbers
f0 = netCDF4.Dataset(files['tag3'][0])
lat = np.asarray(f0['XLAT'][0]); lon = np.asarray(f0['XLONG'][0]); land = np.asarray(f0['LANDMASK'][0]) > 0.5
f0.close()
swna = land & (lat >= 20) & (lat <= 45) & (lon >= -125) & (lon <= -95)
wgt = np.cos(np.deg2rad(lat)) * swna


def acc_tag(nc, t):           # accumulated tagged precip (mm) since the cold start
    return np.asarray(nc[tagname('TR_RAINNC', t)][0], 'f8') + np.asarray(nc[tagname('TR_RAINC', t)][0], 'f8')


def acc_tot(nc):              # accumulated total precip (mm), bucket-corrected
    x = np.asarray(nc['RAINNC'][0], 'f8') + np.asarray(nc['RAINC'][0], 'f8')
    for b in ('I_RAINNC', 'I_RAINC'):
        if b in nc.variables:
            x = x + 100. * np.asarray(nc[b][0], 'f8')
    return x


def swmean(x):
    return float((x * wgt).sum() / wgt.sum())


series = {r: {'single': [], 'multi': []} for _, r, _ in SINGLE}
tot = []
for i in range(n):
    with netCDF4.Dataset(files['tag3'][i]) as m:
        tot.append(swmean(acc_tot(m)))
        for t, r, _ in SINGLE:
            series[r]['multi'].append(swmean(acc_tag(m, t)))
    for t, r, _ in SINGLE:
        with netCDF4.Dataset(files[r][i]) as s:
            series[r]['single'].append(swmean(acc_tag(s, 1)))
with netCDF4.Dataset(files['tag3'][n - 1]) as m:
    maps = {r: {'multi': acc_tag(m, t)} for t, r, _ in SINGLE}
    ptot = acc_tot(m)
for t, r, _ in SINGLE:
    with netCDF4.Dataset(files[r][n - 1]) as s:
        maps[r]['single'] = acc_tag(s, 1)

lines += ['', 'SWNA land (20-45N, 125-95W), cos-lat weighted, July 1980 accumulated precipitation:',
          '   total precipitation           %.4f mm' % tot[-1]]
for _, r, lab in SINGLE:
    a, b = series[r]['single'][-1], series[r]['multi'][-1]
    lines.append('   %-15s single-tag %.6f mm (%.4f of total) | 3-tag %.6f mm (%.4f of total) | diff %.1e'
                 % (lab, a, a / max(tot[-1], 1e-30), b, b / max(tot[-1], 1e-30), b - a))
open('%s/compare_report.txt' % M, 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))

# ---- figure
sub = (lat[:, 0] >= 0) & (lat[:, 0] <= 60)
sx = (lon[0] >= -160) & (lon[0] <= -60)
ext = [lon[0][sx].min(), lon[0][sx].max(), lat[:, 0][sub].min(), lat[:, 0][sub].max()]
cut = lambda a: a[np.ix_(sub, sx)]
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': '#888', 'axes.labelcolor': '#333',
                     'xtick.color': '#555', 'ytick.color': '#555'})
fig = plt.figure(figsize=(12, 13))
gs = fig.add_gridspec(4, 3, height_ratios=[1, 1, 1, 0.9], hspace=0.32, wspace=0.22)
for row, (t, r, lab) in enumerate(SINGLE):
    a, b = maps[r]['single'], maps[r]['multi']
    vmax = np.nanpercentile(cut(a), 99.5) or 1.
    d = b - a
    dl = max(np.nanmax(np.abs(d)), 1e-12)
    for col, (fld, ttl, cmap, lim) in enumerate([
            (a, 'single-tag run (%s only)' % lab, 'Blues', (0, vmax)),
            (b, '3-tag run, tag %d' % t, 'Blues', (0, vmax)),
            (d, '3-tag minus single-tag  (max |diff| = %.1e mm)' % np.nanmax(np.abs(d)), 'RdBu_r', (-dl, dl))]):
        ax = fig.add_subplot(gs[row, col])
        if col == 2 and np.nanmax(np.abs(d)) == 0.:
            ax.imshow(np.zeros_like(cut(fld)), origin='lower', extent=ext, cmap='Greys', vmin=0, vmax=10,
                      aspect='auto')
            ax.text(0.5, 0.5, 'difference = 0\nat every grid point', transform=ax.transAxes, ha='center',
                    va='center', fontsize=11, color='#222',
                    bbox=dict(fc='white', ec='#888', boxstyle='round,pad=0.4'))
            ttl = '3-tag minus single-tag'
        else:
          im = ax.imshow(cut(fld), origin='lower', extent=ext, cmap=cmap, vmin=lim[0], vmax=lim[1],
                         aspect='auto', interpolation='nearest')
        ax.contour(lon[0][sx], lat[:, 0][sub], cut(land.astype(float)), [0.5], colors='#444', linewidths=0.4)
        ax.set_title(ttl, fontsize=9, color='#222')
        if col == 0:
            ax.set_ylabel('%s tag\nlatitude' % lab)
        else:
            ax.tick_params(labelleft=False)
        if col < 2 or np.nanmax(np.abs(d)) > 0.:
            cb = fig.colorbar(im, cax=ax.inset_axes([1.02, 0, 0.035, 1]))
ax = fig.add_subplot(gs[3, :])
day = np.arange(n)
for _, r, lab in SINGLE:
    ax.plot(day, series[r]['single'], color=COLOR[r], lw=2, label='%s, single-tag run' % lab)
    ax.plot(day, series[r]['multi'], ls='none', marker='o', ms=8, mfc='none', mec=COLOR[r], mew=1.5,
            label='%s, 3-tag run' % lab)
ax.set_xticks(day[::5]); ax.set_xticklabels([dates[i][5:] for i in day[::5]])
ax.set_ylabel('SWNA-mean tagged precip,\naccumulated since Jul 1 (mm)')
ax.grid(color='#ddd', lw=0.5); ax.set_axisbelow(True)
for s in ('top', 'right'):
    ax.spines[s].set_visible(False)
ax.legend(ncol=3, fontsize=8, frameon=False, loc='upper left')
fig.suptitle('WRF-WVT multi-tag check, July 1980: one 3-tag run vs three single-tag runs (same domain, forcing, MPI layout)\n'
             'July tagged precipitation (grid-scale + cumulus rain, mm) by source region', fontsize=11)
fig.savefig('%s/compare_july1980.png' % M, dpi=130, bbox_inches='tight')
print('wrote', '%s/compare_july1980.png' % M)

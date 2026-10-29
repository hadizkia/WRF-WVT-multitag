#!/bin/bash
# metgrid (full 941x421 domain, 3-hourly ERA5) + multi-tag real.exe (tracer_opt=43) for 1980-07-01..08-01
#SBATCH --account=hzhang
#SBATCH --partition=batch
#SBATCH -N 2 --ntasks-per-node=48 --mem-per-cpu=2G
#SBATCH --time=12:00:00
#SBATCH --job-name=mt1m_prep
#SBATCH --output=/project/ychoi/hzangane/WRF_WVT_multitag_test/month1/logs/prep.%j.log
set -u
source /project/ychoi/hzangane/WRF_WVT_multitag_test/month1/common.sh
rm -rf $M/input; mkdir -p $M/input; cd $M/input
ln -sf $P/templates/geo_em.d01.nc .
cat > namelist.wps <<EOW
&share
 wrf_core = 'ARW', max_dom = 1,
 start_date = '1980-07-01_00:00:00', end_date = '1980-08-01_00:00:00',
 interval_seconds = 10800, io_form_geogrid = 2, opt_output_from_geogrid_path = './',
/
&geogrid
 parent_id = 1, parent_grid_ratio = 1, i_parent_start = 1, j_parent_start = 1, e_we = 941, e_sn = 421,
/
&ungrib
 out_format = 'WPS', prefix = 'ERA5',
/
&metgrid
 fg_name = '$M/era5/ERA5', io_form_metgrid = 2, opt_metgrid_tbl_path = '$P/templates/',
/
EOW
t0=$(date +%s)
mpirun -np $SLURM_NTASKS $P/bin/metgrid.exe > metgrid.out 2>&1
n=$(ls met_em.d01.* 2>/dev/null | wc -l); echo "met_em: $n (expect 249) in $(( $(date +%s)-t0 )) s"
[ $n -eq 249 ] || { tail -30 metgrid.out; exit 1; }
mknl 43; links
mpirun -np $SLURM_NTASKS $NEW/real.exe
grep -q "SUCCESS COMPLETE REAL_EM" rsl.error.0000 || { echo "real.exe FAILED"; tail -30 rsl.error.0000; exit 1; }
mkdir -p rsl; mv rsl.* rsl/
ls -la wrfinput_d01 wrfbdy_d01 wrflowinp_d01 wrffdda_d01
rm -f met_em.d01.*          # 249 x ~0.5 GB, no longer needed
touch READY; echo "prep done in $(( $(date +%s)-t0 )) s"

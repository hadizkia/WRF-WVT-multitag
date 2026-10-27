#!/bin/bash
# 3-tag test on the original full domain (941 x 421, 30S-75N), 1980-04-01 00-12 UTC, ERA5 + u/v nudging.
#   npac / gom / ll : production (single-tag) WRF-WVT, tracer_opt=4, TRMASK = North Pacific / Gulf of Mexico / Local Land
#   tag3            : multi-tag wrf.exe, tracer_opt=43, TRMASK = npac, TRMASK_T2 = gom, TRMASK_T3 = ll
# Expected: tag3's model fields = the single-tag runs', and tag k = the matching single-tag run's tracer.
#SBATCH --account=hzhang
#SBATCH --partition=batch
#SBATCH -N 4 --ntasks-per-node=48 --mem-per-cpu=2G
#SBATCH --time=04:00:00
#SBATCH --job-name=wvt_mt_test3
#SBATCH --output=/project/ychoi/hzangane/WRF_WVT_multitag_test/test3/logs/run_test3.%j.log
set -u
T=/project/ychoi/hzangane/WRF_WVT_multitag_test/test3
E=/project/ychoi/hzangane/WRF_WVT_multitag_test/era5   # ERA5 WPS intermediate, 1980-04-01 00..12
P=/project/ychoi/hzangane/WRF_WVT_nudgeUV
NEW=/project/hzhang/hzangane/WRF-4.3.3-multitag/main
PROD=$P/bin
NP=$SLURM_NTASKS
module purge; module load netCDF-Fortran/4.6.1-iimpi-2023a
export I_MPI_FABRICS=shm:ofi FI_PROVIDER=verbs
cd $T
[ -x $NEW/wrf.exe ] && [ -x $NEW/real.exe ] || { echo "multi-tag build missing"; exit 1; }

mknl () {   # $1 tracer_opt
  sed -e "s/@SY@/1980/" -e "s/@SM@/04/" -e "s/@SD@/01/" -e "s/@SH@/00/" \
      -e "s/@EY@/1980/" -e "s/@EM@/04/" -e "s/@ED@/01/" -e "s/@EH@/12/" \
      -e "s/@RESTART@/.false./" -e "s/@RSTMIN@/100000/" -e "s/@INTERVAL@/10800/" \
      -e "s/@EWE@/941/" -e "s/@ESN@/421/" -e "s/@NPX@/-1/" -e "s/@NPY@/-1/" \
      -e "/iofields_filename/d" -e "/ignore_iofields_warning/d" \
      -e "s/history_interval .*/history_interval         = 180,/" \
      -e "s/frames_per_outfile .*/frames_per_outfile       = 5,/" \
      -e "s/tracer_opt  .*/tracer_opt               = $1,/" \
      $P/templates/namelist_template.input > namelist.input
}
links () { for f in $P/tables/*; do ln -sf $f .; done; }

if [ ! -f input/READY ]; then
  rm -rf input; mkdir -p input; cd input
  ln -sf $P/templates/geo_em.d01.nc .
  cat > namelist.wps <<EOF
&share
 wrf_core = 'ARW', max_dom = 1,
 start_date = '1980-04-01_00:00:00', end_date = '1980-04-01_12:00:00',
 interval_seconds = 10800, io_form_geogrid = 2, opt_output_from_geogrid_path = './',
/
&geogrid
 parent_id = 1, parent_grid_ratio = 1, i_parent_start = 1, j_parent_start = 1, e_we = 941, e_sn = 421,
/
&ungrib
 out_format = 'WPS', prefix = 'ERA5',
/
&metgrid
 fg_name = '$E/ERA5', io_form_metgrid = 2, opt_metgrid_tbl_path = '$P/templates/',
/
EOF
  mpirun -np 48 $P/bin/metgrid.exe > metgrid.out 2>&1
  echo "met_em: $(ls met_em.d01.* 2>/dev/null | wc -l) (expect 5)"
  mknl 43; links
  mpirun -np 48 $NEW/real.exe
  grep -q "SUCCESS COMPLETE REAL_EM" rsl.error.0000 || { echo "real.exe FAILED"; tail -30 rsl.error.0000; exit 1; }
  mkdir -p rsl; mv rsl.* rsl/; touch READY; cd $T
fi

run () {  # name exe tracer_opt mask
  local d=$T/runs/$1
  [ -f $d/DONE ] && { echo "$1 already done"; return; }
  rm -rf $d; mkdir -p $d/wrfout; cd $d
  mknl $3; links
  for f in wrfinput_d01 wrfbdy_d01 wrflowinp_d01 wrffdda_d01; do ln -sf $T/input/$f .; done
  ln -sf $T/masks/$4 trmask_d01
  local t0=$(date +%s)
  mpirun -np $NP $2/wrf.exe
  if grep -q "SUCCESS COMPLETE WRF" rsl.error.0000; then
    echo "$1: OK in $(( $(date +%s) - t0 )) s"; touch DONE
  else
    echo "$1: FAILED"; tail -40 rsl.error.0000
  fi
  mkdir -p rsl; mv rsl.* rsl/ 2>/dev/null; cd $T
}
run npac $PROD 4  trmask_npac
run gom  $PROD 4  trmask_gom
run ll   $PROD 4  trmask_ll
run tag3 $NEW  43 trmask_3tag

/project/ychoi/hzangane/CONDA_AI/bin/python3 $T/compare_3tag.py $T

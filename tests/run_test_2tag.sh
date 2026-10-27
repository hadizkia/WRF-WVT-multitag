#!/bin/bash
# Multi-tag WRF-WVT validation, regions small domain, 1980-04-01 00-12 UTC (ERA5 boundaries, u/v nudging).
#   prep : metgrid + NEW real.exe (tracer_opt=42, so wrfinput/wrfbdy carry the tag-2 species too)
#   A_prod  production wrf.exe  tracer_opt=4   TRMASK=LL
#   A_new   multi-tag  wrf.exe  tracer_opt=4   TRMASK=LL                 -> must equal A_prod bit for bit
#   AA      multi-tag  wrf.exe  tracer_opt=42  TRMASK=LL, TRMASK_T2=LL   -> model = A_prod, tag1 = tag2 = A_prod tag
#   AB      multi-tag  wrf.exe  tracer_opt=42  TRMASK=LL, TRMASK_T2=~LL  -> model = A_prod, tag1 = A_prod, tag2 = B_prod
#   B_prod  production wrf.exe  tracer_opt=4   TRMASK=~LL
#SBATCH --account=hzhang
#SBATCH --partition=batch
#SBATCH -N 1 --ntasks-per-node=48 --mem-per-cpu=1G
#SBATCH --time=02:00:00
#SBATCH --job-name=wvt_mt_test
#SBATCH --output=/project/ychoi/hzangane/WRF_WVT_multitag_test/logs/run_tests.%j.log
set -u
T=/project/ychoi/hzangane/WRF_WVT_multitag_test
P=/project/ychoi/hzangane/WRF_WVT_nudgeUV          # production setup (tables, templates, metgrid, geo_em)
NEW=/project/hzhang/hzangane/WRF-4.3.3-multitag/main
PROD=$P/bin
module purge; module load netCDF-Fortran/4.6.1-iimpi-2023a
export I_MPI_FABRICS=shm:ofi FI_PROVIDER=verbs
cd $T
[ -x $NEW/wrf.exe ] && [ -x $NEW/real.exe ] || { echo "multi-tag build missing: $NEW/wrf.exe / real.exe"; exit 1; }

mknl () {   # $1 tracer_opt -> namelist.input in cwd
  sed -e "s/@SY@/1980/" -e "s/@SM@/04/" -e "s/@SD@/01/" -e "s/@SH@/00/" \
      -e "s/@EY@/1980/" -e "s/@EM@/04/" -e "s/@ED@/01/" -e "s/@EH@/12/" \
      -e "s/@RESTART@/.false./" -e "s/@RSTMIN@/100000/" -e "s/@INTERVAL@/10800/" \
      -e "s/@EWE@/121/" -e "s/@ESN@/101/" -e "s/@NPX@/-1/" -e "s/@NPY@/-1/" \
      -e "/iofields_filename/d" -e "/ignore_iofields_warning/d" \
      -e "s/history_interval .*/history_interval         = 180,/" \
      -e "s/frames_per_outfile .*/frames_per_outfile       = 5,/" \
      -e "s/tracer_opt  .*/tracer_opt               = $1,/" \
      $P/templates/namelist_template.input > namelist.input
}
links () { for f in $P/tables/*; do ln -sf $f .; done; }

# ---------------- prep
if [ ! -f input/READY ]; then
  rm -rf input; mkdir -p input; cd input
  ln -sf $P/domains/regions/geo_em.d01.nc .
  cat > namelist.wps <<EOF
&share
 wrf_core = 'ARW', max_dom = 1,
 start_date = '1980-04-01_00:00:00', end_date = '1980-04-01_12:00:00',
 interval_seconds = 10800, io_form_geogrid = 2, opt_output_from_geogrid_path = './',
/
&geogrid
 parent_id = 1, parent_grid_ratio = 1, i_parent_start = 1, j_parent_start = 1, e_we = 121, e_sn = 101,
/
&ungrib
 out_format = 'WPS', prefix = 'ERA5',
/
&metgrid
 fg_name = '$T/era5/ERA5', io_form_metgrid = 2, opt_metgrid_tbl_path = '$P/templates/',
/
EOF
  mpirun -np 16 $P/bin/metgrid.exe > metgrid.out 2>&1
  echo "met_em: $(ls met_em.d01.* | wc -l) (expect 5)"
  mknl 42; links
  mpirun -np 16 $NEW/real.exe
  grep -q "SUCCESS COMPLETE REAL_EM" rsl.error.0000 || { echo "real.exe FAILED"; tail -30 rsl.error.0000; exit 1; }
  mkdir -p rsl; mv rsl.* rsl/; touch READY; cd $T
fi

# ---------------- runs (each in runs/<name>)
run () {  # name exe tracer_opt mask
  local d=$T/runs/$1
  [ -f $d/DONE ] && { echo "$1 already done"; return; }
  rm -rf $d; mkdir -p $d/wrfout; cd $d
  mknl $3; links
  for f in wrfinput_d01 wrfbdy_d01 wrflowinp_d01 wrffdda_d01; do ln -sf $T/input/$f .; done
  ln -sf $T/masks/$4 trmask_d01
  local t0=$(date +%s)
  mpirun -np 48 $2/wrf.exe
  if grep -q "SUCCESS COMPLETE WRF" rsl.error.0000; then
    echo "$1: OK in $(( $(date +%s) - t0 )) s"; touch DONE
  else
    echo "$1: FAILED"; tail -40 rsl.error.0000
  fi
  mkdir -p rsl; mv rsl.* rsl/ 2>/dev/null; cd $T
}
run A_prod $PROD 4  trmask_A
run A_new  $NEW  4  trmask_A
run AA     $NEW  42 trmask_AA
run AB     $NEW  42 trmask_AB
run B_prod $PROD 4  trmask_B

/project/ychoi/hzangane/CONDA_AI/bin/python3 $T/compare_2tag.py $T

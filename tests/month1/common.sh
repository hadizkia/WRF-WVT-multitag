# shared settings for the 1-month multi-tag vs single-tag test (July 1980, 941 x 421 domain)
M=/project/ychoi/hzangane/WRF_WVT_multitag_test/month1
P=/project/ychoi/hzangane/WRF_WVT_nudgeUV          # production setup: tables, templates, metgrid, single-tag wrf.exe
NEW=/project/hzhang/hzangane/WRF-4.3.3-multitag/main
PROD=$P/bin
module purge; module load netCDF-Fortran/4.6.1-iimpi-2023a
export I_MPI_FABRICS=shm:ofi FI_PROVIDER=verbs
mknl () {   # $1 tracer_opt -> namelist.input in cwd; daily full-field history, one file per day
  sed -e "s/@SY@/1980/" -e "s/@SM@/07/" -e "s/@SD@/01/" -e "s/@SH@/00/" \
      -e "s/@EY@/1980/" -e "s/@EM@/08/" -e "s/@ED@/01/" -e "s/@EH@/00/" \
      -e "s/@RESTART@/.false./" -e "s/@RSTMIN@/1000000/" -e "s/@INTERVAL@/10800/" \
      -e "s/@EWE@/941/" -e "s/@ESN@/421/" -e "s/@NPX@/-1/" -e "s/@NPY@/-1/" \
      -e "/iofields_filename/d" -e "/ignore_iofields_warning/d" \
      -e "s/history_interval .*/history_interval         = 1440,/" \
      -e "s/frames_per_outfile .*/frames_per_outfile       = 1,/" \
      -e "s/tracer_opt  .*/tracer_opt               = $1,/" \
      $P/templates/namelist_template.input > namelist.input
}
links () { for f in $P/tables/*; do ln -sf $f .; done; }

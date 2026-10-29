#!/bin/bash
# one 1-month run: sbatch run.sh NAME EXE_DIR TRACER_OPT MASK   (same 192-rank decomposition for all runs)
#SBATCH --account=hzhang
#SBATCH --partition=batch
#SBATCH -N 4 --ntasks-per-node=48 --mem-per-cpu=2G
#SBATCH --time=24:00:00
#SBATCH --output=/project/ychoi/hzangane/WRF_WVT_multitag_test/month1/logs/run_%x.%j.log
set -u
source /project/ychoi/hzangane/WRF_WVT_multitag_test/month1/common.sh
name=$1 exe=$2 topt=$3 mask=$4
[ -f $M/input/READY ] || { echo "prep not done"; exit 1; }
d=$M/runs/$name; rm -rf $d; mkdir -p $d/wrfout; cd $d
mknl $topt; links
for f in wrfinput_d01 wrfbdy_d01 wrflowinp_d01 wrffdda_d01; do ln -sf $M/input/$f .; done
ln -sf $M/masks/$mask trmask_d01
echo "$name: $exe/wrf.exe tracer_opt=$topt mask=$mask ranks=$SLURM_NTASKS nodes=$SLURM_JOB_NODELIST"
t0=$(date +%s)
mpirun -np $SLURM_NTASKS $exe/wrf.exe
if grep -q "SUCCESS COMPLETE WRF" rsl.error.0000; then
  echo "$name: OK in $(( $(date +%s) - t0 )) s"; touch DONE
else
  echo "$name: FAILED"; tail -40 rsl.error.0000
fi
mkdir -p rsl; mv rsl.* rsl/ 2>/dev/null

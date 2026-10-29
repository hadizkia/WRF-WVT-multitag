#!/bin/bash
#SBATCH --account=hzhang
#SBATCH --partition=batch
#SBATCH -N 1 -n 1 --mem=64G
#SBATCH --time=06:00:00
#SBATCH --job-name=mt1m_cmp
#SBATCH --output=/project/ychoi/hzangane/WRF_WVT_multitag_test/month1/logs/compare.%j.log
/project/ychoi/hzangane/CONDA_AI/bin/python3 /project/ychoi/hzangane/WRF_WVT_multitag_test/month1/compare_month.py /project/ychoi/hzangane/WRF_WVT_multitag_test/month1

#!/bin/bash
# Apply the multi-tag patch to a WRF 4.3.3 tree that already has the WRF-WVTs modules.
#
#   ./install.sh /path/to/WRF-4.3.3            # default: 10 tags
#   ./install.sh /path/to/WRF-4.3.3 20         # a different maximum number of tags
#
# Then build WRF as usual (./configure once, ./compile em_real).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
WRF=${1:?usage: install.sh /path/to/WRF-4.3.3 [max_tags]}
MAX=${2:-10}
cd "$WRF"

[ -f phys/module_mp_wsm6_tr.F ] && [ -f Registry/registry.moisttracers ] || {
  echo "ERROR: $WRF has no WRF-WVTs modules. Unpack modules_tracers_4.3.3.tar from"
  echo "       https://github.com/damianinsua/WRF-WVTs into it first."; exit 1; }
[ -f share/module_wvt_tags.F ] && { echo "ERROR: the multi-tag patch is already applied in $WRF"; exit 1; }

patch -p1 --dry-run < "$HERE/patch/wrf-wvt-multitag.patch" > /dev/null
patch -p1 < "$HERE/patch/wrf-wvt-multitag.patch"
if [ "$MAX" != 10 ]; then python3 tools/wvt_multitag/gen_wvt_multitag.py "$MAX"; fi
rm -f Registry/Registry   # make ./compile regenerate it from Registry.EM
echo
echo "Multi-tag WRF-WVT installed in $WRF (up to $MAX tags)."
echo "Build as usual:  ./configure  (once)  then  ./compile em_real"

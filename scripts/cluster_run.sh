#!/bin/bash
# SubCellSpace runner for cluster (no-internet, copied env)
export PATH="$HOME/miniconda3/envs/subcellspace/bin:$PATH"
cd "$HOME/zf-li23/subcellspace"
exec python "$@"

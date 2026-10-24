#!/bin/bash
# NLVL pilot - run the whole study end to end.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"   # repository root
PY=${PY:-python3}   # override: PY=/path/to/python bash scripts/run_all.sh
cd $ROOT

echo "### encoding BioMedCLIP"
$PY scripts/01_encode.py --model biomedclip 2>&1 | grep -E "encoded in|wrote|ERROR|Error|error" || echo "  biomedclip FAILED"

MODELS="clip clip_l14 clip_l14_squash clip_l14_zoom biomedclip"
for M in $MODELS; do
  [ -f outputs/$M/embeddings.npz ] || { echo "### skip $M (no embeddings)"; continue; }
  echo "### $M"
  $PY scripts/02_localise.py --model $M 2>&1 | grep -E "tau_|Error" 
  $PY scripts/03_evaluate.py --model $M 2>&1 | sed -n '/=== /,/^$/p'
done

echo "### figures"
for M in $MODELS; do
  [ -f outputs/$M/results.json ] && $PY scripts/04_figures.py --model $M 2>&1 | grep -E "figures|Error"
done
$PY scripts/04_figures.py --model clip_l14 --all-models $MODELS 2>&1 | grep -E "figures|Error"
echo "### done"

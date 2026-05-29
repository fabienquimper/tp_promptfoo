#!/bin/sh
# Contourne le bug de résolution de {{env.LLM_MODEL}} dans la section providers de promptfoo.
# Usage : sh /app/eval.sh [config_path] [args promptfoo supplémentaires...]
if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then
  CONFIG="$1"; shift
else
  CONFIG="/app/promptfooconfig.yaml"
fi
TMPCONFIG="$(dirname "$CONFIG")/.pf_eval_tmp.yaml"
sed "s|{{env.LLM_MODEL}}|$LLM_MODEL|g" "$CONFIG" > "$TMPCONFIG"
promptfoo eval -c "$TMPCONFIG" "$@"

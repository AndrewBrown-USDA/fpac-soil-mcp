#!/usr/bin/env bash
# Idempotent setup of Node/npm and the Databricks MCP libraries on Databricks
# serverless compute when no notebook environment is in use (for example, Genie
# Code shell commands).
#
# Usage, at the start of each new shell (a fast no-op once installed):
#   source databricks/bootstrap-serverless.sh
#
# Pins come from databricks/serverless-environment.yaml, the single source of
# truth. Tools install under /tmp, which is wiped when serverless compute
# restarts; sourcing again after a restart reinstalls them.
#
# Exports:
#   PATH                    node, npm, and npx wrappers prepended
#   FPAC_SERVERLESS_PYTHON  venv Python with databricks-mcp and databricks-sdk

_fpac_bootstrap() {
  local root spec venv bin stamp pins nw
  root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || return 1
  spec="$root/databricks/serverless-environment.yaml"
  venv="${FPAC_SERVERLESS_VENV:-/tmp/fpac-serverless-venv}"
  bin="$venv/wrappers"
  stamp="$venv/.pins"

  pins="$(python3 -c 'import sys, yaml; print("\n".join(yaml.safe_load(open(sys.argv[1]))["dependencies"]))' "$spec")" ||
    { echo "bootstrap: cannot read $spec" >&2; return 1; }

  if [ ! -f "$stamp" ] || [ "$(cat "$stamp")" != "$pins" ] || [ ! -x "$bin/npm" ]; then
    echo "bootstrap: installing pinned tools into $venv" >&2
    uv venv -q --clear "$venv" --python "$(command -v python3)" || return 1
    # Word splitting is intended: one pin per line.
    # shellcheck disable=SC2086
    uv pip install -q --python "$venv/bin/python" $pins || return 1
    nw="$("$venv/bin/python" -c 'import nodejs_wheel, os; print(os.path.dirname(nodejs_wheel.__file__))')" || return 1
    # The wheel's own npm/npx shims fail (MODULE_NOT_FOUND); call the CLIs through node.
    mkdir -p "$bin"
    printf '#!/bin/sh\nexec "%s/bin/node" "$@"\n' "$nw" >"$bin/node"
    printf '#!/bin/sh\nexec "%s/bin/node" "%s/lib/node_modules/npm/bin/npm-cli.js" "$@"\n' "$nw" "$nw" >"$bin/npm"
    printf '#!/bin/sh\nexec "%s/bin/node" "%s/lib/node_modules/npm/bin/npx-cli.js" "$@"\n' "$nw" "$nw" >"$bin/npx"
    chmod +x "$bin/node" "$bin/npm" "$bin/npx"
    printf '%s' "$pins" >"$stamp"
    echo "bootstrap: node $("$bin/node" --version), npm $("$bin/npm" --version)" >&2
  fi

  case ":$PATH:" in
    *":$bin:"*) ;;
    *) PATH="$bin:$PATH" ;;
  esac
  export PATH
  export FPAC_SERVERLESS_PYTHON="$venv/bin/python"
}

_fpac_rc=0
_fpac_bootstrap || _fpac_rc=$?
unset -f _fpac_bootstrap
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  # Executed rather than sourced: tools are installed, but PATH is not kept.
  [ "$_fpac_rc" -eq 0 ] && echo "bootstrap: ready; run 'source $0' to put node/npm/npx on PATH" >&2
  exit "$_fpac_rc"
fi
return "$_fpac_rc"

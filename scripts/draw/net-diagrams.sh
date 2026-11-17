#!/usr/bin/env bash
# Source: https://github.com/infraguide-org/lab-openstack
# Copyright (c) 2026 infraguide.org, MIT License
#
# Renders the network diagrams with net-diagram.py: env.svg with all networks and,
# for every network of the layout file, env-<id>.svg with that network in focus mode.
# Usage: net-diagrams.sh <env-yaml> <layout-yaml> <out-dir>
# Needs python3 with PyYAML.
set -euo pipefail

[ $# -eq 3 ] || { sed -n '5,8p' "$0" >&2; exit 1; }
env=$1 lay=$2 out=$3
draw="$(dirname "$(realpath "$0")")/net-diagram.py"

mkdir -p "$out"
python3 "$draw" "$env" "$lay" "$out/env.svg"
for id in $(python3 -c 'import sys, yaml
for n in yaml.safe_load(open(sys.argv[1]))["networks"]: print(n["id"])' "$lay"); do
  python3 "$draw" "$env" "$lay" "$out/env-$id.svg" --focus "$id"
done
ls "$out"/env.svg "$out"/env-*.svg

#!/usr/bin/env bash
# Source: https://github.com/infraguide-org/lab-openstack
# Copyright (c) 2026 infraguide.org, MIT License
#
# Writes index.json (machine-readable list of decks and files) and index.html
# (download page) into the built slides directory.
# Usage: make-index.sh <lab> <src-dir> <dist-dir>
set -euo pipefail

lab=$1
src=$(realpath "$2")
cd "$3"

rm -f README.*

decks='[]'
for md in "$src"/*.md; do
  name=$(basename "$md" .md)
  [ "$name" = README ] && continue
  [ -f "$name.html" ] || continue
  title=$(sed -n '/^---$/,/^---$/{s/^title: *//p;}' "$md" | head -1 | sed 's/^"//; s/"$//')
  decks=$(jq -c --arg n "$name" --arg t "${title:-$name}" \
    '. + [{name: $n, title: $t, html: "\($n).html", pdf: "\($n).pdf", pptx: "\($n).pptx"}]' <<<"$decks")
done

files=$(find . -type f ! -name 'index.*' | sed 's#^\./##' | sort | jq -R -s -c 'split("\n") | map(select(length > 0))')

jq -n --arg lab "$lab" --argjson decks "$decks" --argjson files "$files" \
  '{schema: 1, lab: $lab, decks: $decks, files: $files}' > index.json

{
  cat <<HTML
<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${lab} slides | infraguide.org</title>
<style>
  body { font: 16px/1.5 system-ui, sans-serif; max-width: 52rem; margin: 2rem auto; padding: 0 1rem; color: #111; }
  img.logo { height: 44px; display: block; margin-bottom: 1.5rem; }
  table { width: 100%; border-collapse: collapse; table-layout: fixed; }
  th, td { padding: .6rem .8rem; border-bottom: 1px solid #e5e7eb; text-align: left; }
  th:first-child, td:first-child { width: 55%; }
  th:not(:first-child), td:not(:first-child) { width: 15%; text-align: center; }
  a { color: #2b6cb0; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style>
<a href="https://infraguide.org"><img class="logo" src="assets/logo/logo.svg" alt="infraguide.org"></a>
<h1>${lab} slides</h1>
<table>
  <thead><tr><th>Deck</th><th>HTML</th><th>PDF</th><th>PPTX</th></tr></thead>
  <tbody>
HTML
  jq -r '.decks[] | "    <tr><td>\(.title | gsub("&"; "&amp;") | gsub("<"; "&lt;"))</td><td><a href=\"\(.html)\">View</a></td><td><a href=\"\(.pdf)\">Download</a></td><td><a href=\"\(.pptx)\">Download</a></td></tr>"' index.json
  cat <<HTML
  </tbody>
</table>
</html>
HTML
} > index.html

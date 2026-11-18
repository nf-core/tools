#!/usr/bin/env bash
set -euo pipefail

view_pattern='\.view[[:space:]]*(\(|\{)'
dump_pattern='\.dump[[:space:]]*(\(|\{)'

failed=0
view_found=0
dump_found=0

for file in "$@"; do
  if view_matches=$(grep -nE -- "$view_pattern" "$file"); then
    printf 'ERROR: Nextflow .view operator found in %s:\n%s\n' \
      "$file" "$view_matches"
    view_found=1
    failed=1
  else
    status=$?
    if [ "$status" -ne 1 ]; then
      printf 'ERROR: Could not scan %s for .view (grep exit %s).\n' \
        "$file" "$status" >&2
      failed=1
    fi
  fi

  if dump_matches=$(grep -nE -- "$dump_pattern" "$file"); then
    printf 'ERROR: Nextflow .dump operator found in %s:\n%s\n' \
      "$file" "$dump_matches"
    dump_found=1
    failed=1
  else
    status=$?
    if [ "$status" -ne 1 ]; then
      printf 'ERROR: Could not scan %s for .dump (grep exit %s).\n' \
        "$file" "$status" >&2
      failed=1
    fi
  fi
done

if [ "$view_found" -ne 0 ]; then
  printf '\nCommit blocked: remove .view() / .view { ... } before committing.\n'
fi

if [ "$dump_found" -ne 0 ]; then
  printf '\nCommit blocked: remove .dump() / .dump { ... } before committing.\n'
fi

exit "$failed"

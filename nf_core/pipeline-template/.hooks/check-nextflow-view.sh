#!/usr/bin/env bash
set -euo pipefail

pattern='\.view[[:space:]]*(\(|\{)'
failed=0

for file in "$@"; do
  if matches=$(grep -nE -- "$pattern" "$file"); then
    printf 'ERROR: Nextflow .view operator found in %s:\n%s\n' \
      "$file" "$matches"
    failed=1
  else
    status=$?
    if [ "$status" -ne 1 ]; then
      printf 'ERROR: Could not scan %s (grep exit %s).\n' \
        "$file" "$status" >&2
      failed=1
    fi
  fi
done

if [ "$failed" -ne 0 ]; then
  printf '\nCommit blocked: remove .view() / .view { ... } before committing.\n'
fi

exit "$failed"

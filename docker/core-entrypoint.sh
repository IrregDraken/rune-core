#!/bin/sh
set -eu
mkdir -p /app/data
chown -R rune:rune /app/data
exec gosu rune "$@"

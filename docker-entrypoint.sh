#!/bin/sh
set -eu

mkdir -p /app/data /app/exports
chown -R relay:relay /app/data /app/exports

exec gosu relay "$@"

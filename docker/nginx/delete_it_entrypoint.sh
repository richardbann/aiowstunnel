#!/bin/bash
set -e

if [ "$1" = 'nginx' ]; then
  exec nginx -c /nginx.conf
fi

exec "$@"

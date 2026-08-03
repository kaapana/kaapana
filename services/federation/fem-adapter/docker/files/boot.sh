#!/bin/sh
set -e

cd /app/app
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8090}" --access-log

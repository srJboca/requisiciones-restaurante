#!/bin/bash
# Frontend startup script for Azure App Service (Linux, non-containerized)
# Place in the root of the frontend deployment package.
set -e

pip install -r requirements.txt
pip install -q gunicorn polib

# Compile translations if .mo files are missing
if [ ! -f translations/es/LC_MESSAGES/messages.mo ]; then
  echo "Compiling translations..."
  pybabel compile -d translations || true
fi

exec gunicorn -w 2 -b "0.0.0.0:${PORT:-8000}" app:app

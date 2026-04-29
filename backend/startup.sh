#!/bin/bash
# Backend startup script for Azure App Service (Linux, non-containerized)
# Place in the root of the backend deployment package.
set -e

pip install -r requirements.txt

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"

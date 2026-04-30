#!/usr/bin/env bash
# =============================================================================
# La Cesta — Azure Backend Update Script
# =============================================================================
# Use this script to update the backend codebase on Azure without modifying 
# the infrastructure or touching the frontend.
#
# Usage:
#   chmod +x azure/deploy_backend.sh
#   ./azure/deploy_backend.sh
# =============================================================================

set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-lacesta-rg}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PARAMETERS_FILE="$SCRIPT_DIR/parameters.json"

info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[ OK ]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERR ]\033[0m  $*" >&2; exit 1; }

command -v az   >/dev/null 2>&1 || error "Azure CLI not found. Install from https://aka.ms/installazureclimacos"
command -v zip  >/dev/null 2>&1 || error "'zip' not found. Install with: brew install zip"

[[ -f "$PARAMETERS_FILE" ]] || error "parameters.json not found. Copy parameters.example.json → parameters.json and fill in values."

BACKEND_APP=$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['backendAppName']['value'])")

info "Packaging and deploying backend code to $BACKEND_APP..."

BACKEND_ZIP="/tmp/lacesta-backend-update.zip"
cd "$ROOT_DIR/backend"
zip -r "$BACKEND_ZIP" . -x "*.pyc" -x "__pycache__/*" -x ".git/*"

az webapp deploy \
  --resource-group "$RESOURCE_GROUP" \
  --name "$BACKEND_APP" \
  --src-path "$BACKEND_ZIP" \
  --type zip \
  --async false

rm -f "$BACKEND_ZIP"

echo ""
ok "Backend successfully deployed!"
echo "  URL: https://${BACKEND_APP}.azurewebsites.net"
echo "=============================================="

#!/usr/bin/env bash
# =============================================================================
# La Cesta — Azure Frontend Update Script
# =============================================================================
# Use this script to update the frontend codebase on Azure without modifying 
# the infrastructure or touching the backend.
#
# Usage:
#   chmod +x azure/deploy_frontend.sh
#   ./azure/deploy_frontend.sh
# =============================================================================

set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-lacesta-rg}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PARAMETERS_FILE="$SCRIPT_DIR/parameters.json"

info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[ OK ]\033[0m  $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERR ]\033[0m  $*" >&2; exit 1; }

command -v az   >/dev/null 2>&1 || error "Azure CLI not found. Install from https://aka.ms/installazureclimacos"
command -v zip  >/dev/null 2>&1 || error "'zip' not found. Install with: brew install zip"

[[ -f "$PARAMETERS_FILE" ]] || error "parameters.json not found. Copy parameters.example.json → parameters.json and fill in values."

FRONTEND_APP=$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['frontendAppName']['value'])")

info "Packaging and deploying frontend code to $FRONTEND_APP..."

FRONTEND_ZIP="/tmp/lacesta-frontend-update.zip"
cd "$ROOT_DIR/frontend"
zip -r "$FRONTEND_ZIP" . \
  -x "*.pyc" -x "__pycache__/*" -x ".git/*" \
  -x "translations/*/LC_MESSAGES/*.mo"

az webapp deploy \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FRONTEND_APP" \
  --src-path "$FRONTEND_ZIP" \
  --type zip \
  --async false

rm -f "$FRONTEND_ZIP"
ok "Frontend deployed to Azure App Service."

info "Compiling translations on the frontend App Service..."
KUDU_CREDS=$(az webapp deployment list-publishing-credentials \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FRONTEND_APP" \
  --query "{user:publishingUserName,pwd:publishingPassword}" -o json)

KUDU_USER=$(echo "$KUDU_CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['user'])")
KUDU_PWD=$(echo "$KUDU_CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['pwd'])")

curl -s -X POST \
  "https://${FRONTEND_APP}.scm.azurewebsites.net/api/command" \
  -u "${KUDU_USER}:${KUDU_PWD}" \
  -H "Content-Type: application/json" \
  -d "{\"command\":\"pip install polib && pybabel compile -d /home/site/wwwroot/translations\",\"dir\":\"/home/site/wwwroot\"}" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('Output',''))"

ok "Translations compiled."

echo ""
ok "Frontend successfully deployed!"
echo "  URL: https://${FRONTEND_APP}.azurewebsites.net"
echo "=============================================="

#!/usr/bin/env bash
# =============================================================================
# La Cesta — Azure Deployment Script
# =============================================================================
# Prerequisites:
#   - Azure CLI installed and logged in  (az login)
#   - zip utility installed
#   - mysql client installed (for DB init)
#   - azure/parameters.json filled in (copy from parameters.example.json)
#
# Usage:
#   chmod +x azure/deploy.sh
#   ./azure/deploy.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — edit these or override as environment variables
# ---------------------------------------------------------------------------
RESOURCE_GROUP="${RESOURCE_GROUP:-lacesta-rg}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PARAMETERS_FILE="$SCRIPT_DIR/parameters.json"
TEMPLATE_FILE="$SCRIPT_DIR/arm-template.json"

# Location is read from parameters.json (can still be overridden via LOCATION env var)
LOCATION="${LOCATION:-$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['location']['value'])")}"

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[ OK ]\033[0m  $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERR ]\033[0m  $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Verify prerequisites
# ---------------------------------------------------------------------------
command -v az   >/dev/null 2>&1 || error "Azure CLI not found. Install from https://aka.ms/installazureclimacos"
command -v zip  >/dev/null 2>&1 || error "'zip' not found. Install with: brew install zip"
command -v mysql>/dev/null 2>&1 || warn "mysql client not found — DB init step will be skipped"

[[ -f "$PARAMETERS_FILE" ]] || error "parameters.json not found. Copy parameters.example.json → parameters.json and fill in values."

# ---------------------------------------------------------------------------
# Read key values from parameters file (requires jq or az CLI parsing)
# ---------------------------------------------------------------------------
MYSQL_SERVER=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name lacesta-deploy --query "properties.outputs.mysqlFqdn.value" -o tsv 2>/dev/null || true)
BACKEND_APP=$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['backendAppName']['value'])")
FRONTEND_APP=$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['frontendAppName']['value'])")
MYSQL_SERVER_NAME=$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['mysqlServerName']['value'])")
MYSQL_ADMIN=$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['mysqlAdminLogin']['value'])")
MYSQL_PASSWORD=$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['mysqlAdminPassword']['value'])")
DB_NAME=$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['databaseName']['value'])")
DB_APP_USER=$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['dbAppUser']['value'])")
DB_APP_PASSWORD=$(python3 -c "import json; d=json.load(open('$PARAMETERS_FILE')); print(d['parameters']['dbAppPassword']['value'])")

# ---------------------------------------------------------------------------
# Step 1 — Create Resource Group
# ---------------------------------------------------------------------------
info "Step 1 — Creating resource group '$RESOURCE_GROUP' in '$LOCATION'..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none
ok "Resource group ready."

# ---------------------------------------------------------------------------
# Step 2 — Deploy ARM Template (infrastructure)
# ---------------------------------------------------------------------------

CREATE_ASP="true"
ASP_ID=""
read -p "Do you want to reuse an existing App Service Plan? (y/N): " reuse_asp
if [[ "$reuse_asp" =~ ^[Yy]$ ]]; then
    CREATE_ASP="false"
    read -p "Enter the full resource ID of the existing App Service Plan: " ASP_ID
fi

CREATE_MYSQL="true"
EXISTING_MYSQL_FQDN=""
read -p "Do you want to reuse an existing MySQL Flexible Server? (y/N): " reuse_mysql
if [[ "$reuse_mysql" =~ ^[Yy]$ ]]; then
    CREATE_MYSQL="false"
    read -p "Enter the existing MySQL FQDN (e.g. myserver.mysql.database.azure.com): " EXISTING_MYSQL_FQDN
    read -p "Enter the MySQL Admin username (e.g. admin_user): " MYSQL_ADMIN
    read -sp "Enter the MySQL Admin password: " MYSQL_PASSWORD
    echo "" # To ensure the next output is on a new line after the silent password prompt
fi

info "Step 2 — Deploying infrastructure (MySQL + App Service Plan + Web Apps)..."
if [[ "$CREATE_MYSQL" == "false" ]]; then
    info "  Skipping MySQL creation. Using existing database..."
    TEMPLATE_FILE="$SCRIPT_DIR/arm-template-nodb.json"
else
    info "  This can take 5–10 minutes for MySQL provisioning..."
fi

az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --name "lacesta-deploy" \
  --template-file "$TEMPLATE_FILE" \
  --parameters "@$PARAMETERS_FILE" \
  --parameters createMySql="$CREATE_MYSQL" \
  --parameters existingMysqlFqdn="$EXISTING_MYSQL_FQDN" \
  --parameters createAppServicePlan="$CREATE_ASP" \
  --parameters existingAppServicePlanId="$ASP_ID" \
  --output table

MYSQL_FQDN=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name "lacesta-deploy" \
  --query "properties.outputs.mysqlFqdn.value" -o tsv)

BACKEND_URL=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name "lacesta-deploy" \
  --query "properties.outputs.backendUrl.value" -o tsv)

FRONTEND_URL=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name "lacesta-deploy" \
  --query "properties.outputs.frontendUrl.value" -o tsv)

ok "Infrastructure deployed."
info "  MySQL FQDN : $MYSQL_FQDN"
info "  Backend URL: $BACKEND_URL"
info "  Frontend URL: $FRONTEND_URL"

# ---------------------------------------------------------------------------
# Step 3 — Initialize the database (schema + admin seed)
# ---------------------------------------------------------------------------
info "Step 3 — Initializing database schema..."

if command -v mysql >/dev/null 2>&1; then
  # Allow a moment for MySQL to finish provisioning firewall rules
  sleep 10

  # Run init.sql as the admin user
  mysql \
    --host="$MYSQL_FQDN" \
    --user="$MYSQL_ADMIN" \
    --password="$MYSQL_PASSWORD" \
    --ssl-mode=REQUIRED \
    < "$ROOT_DIR/db/init.sql"

  # Create the api_user and grant permissions
  mysql \
    --host="$MYSQL_FQDN" \
    --user="$MYSQL_ADMIN" \
    --password="$MYSQL_PASSWORD" \
    --ssl-mode=REQUIRED \
    <<SQL
CREATE USER IF NOT EXISTS '${DB_APP_USER}'@'%' IDENTIFIED BY '${DB_APP_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_APP_USER}'@'%';
FLUSH PRIVILEGES;
SQL

  ok "Database initialized."
else
  warn "mysql client not found — skipping automatic DB init."
  warn "Run manually after deployment:"
  warn "  mysql --host=$MYSQL_FQDN --user=$MYSQL_ADMIN --password=<pwd> --ssl-mode=REQUIRED < db/init.sql"
fi

# ---------------------------------------------------------------------------
# Step 4 — Deploy backend code
# ---------------------------------------------------------------------------
info "Step 4 — Packaging and deploying backend..."

BACKEND_ZIP="/tmp/lacesta-backend.zip"
cd "$ROOT_DIR/backend"
zip -r "$BACKEND_ZIP" . -x "*.pyc" -x "__pycache__/*" -x ".git/*"

az webapp deploy \
  --resource-group "$RESOURCE_GROUP" \
  --name "$BACKEND_APP" \
  --src-path "$BACKEND_ZIP" \
  --type zip \
  --async false

rm -f "$BACKEND_ZIP"
ok "Backend deployed to $BACKEND_URL"

# ---------------------------------------------------------------------------
# Step 5 — Deploy frontend code
# ---------------------------------------------------------------------------
info "Step 5 — Packaging and deploying frontend..."

# Update CORS in backend to allow the actual frontend URL
info "  Updating backend CORS to allow $FRONTEND_URL..."
az webapp cors add \
  --resource-group "$RESOURCE_GROUP" \
  --name "$BACKEND_APP" \
  --allowed-origins "$FRONTEND_URL" \
  --output none

FRONTEND_ZIP="/tmp/lacesta-frontend.zip"
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
ok "Frontend deployed to $FRONTEND_URL"

# ---------------------------------------------------------------------------
# Step 6 — Compile translations inside the frontend app
# ---------------------------------------------------------------------------
info "Step 6 — Compiling translations on the frontend App Service..."

az webapp ssh --resource-group "$RESOURCE_GROUP" --name "$FRONTEND_APP" 2>/dev/null || \
  warn "SSH not available — compile translations manually by running:"
  warn "  pybabel compile -d translations"

# Use Kudu REST API to run the compile command remotely
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

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "  DEPLOYMENT COMPLETE"
echo "=============================================="
echo "  Frontend : $FRONTEND_URL"
echo "  Backend  : $BACKEND_URL"
echo "  API Docs : ${BACKEND_URL}/docs"
echo "  MySQL    : $MYSQL_FQDN"
echo ""
echo "  Default login: admin / admin123"
echo "  IMPORTANT: Change the admin password immediately!"
echo "=============================================="

# Azure Deployment — La Cesta Requisition System

This directory contains everything needed to deploy the application to Microsoft Azure as **non-containerized Linux App Services**.

## Architecture on Azure

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   Azure Resource Group                  │
│                                                         │
│  ┌───────────────────┐    ┌───────────────────────────┐ │
│  │  Frontend App Svc │───▶│   Backend App Service     │ │
│  │  Flask / Python   │    │  FastAPI / Python 3.11    │ │
│  │  lacesta-frontend │    │  lacesta-backend          │ │
│  └───────────────────┘    └─────────────┬─────────────┘ │
│                                         │               │
│                           ┌─────────────▼─────────────┐ │
│                           │  MySQL Flexible Server    │ │
│                           │  lacesta-mysql            │ │
│                           └───────────────────────────┘ │
│                                                         │
│  (All on a shared Linux App Service Plan: lacesta-asp)  │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-macos) installed
- Active Azure subscription
- `zip` command available (`brew install zip`)
- `mysql` client available (`brew install mysql-client`) — needed only for DB init

```bash
# Log in to Azure
az login
```

## Files

| File | Description |
|---|---|
| `arm-template.json` | ARM template — creates MySQL, App Service Plan, backend & frontend Web Apps |
| `parameters.example.json` | Parameter template — copy and fill in before deploying |
| `deploy.sh` | One-command end-to-end deployment script |

## Step-by-Step Deployment

### 1. Create your parameters file

```bash
cp azure/parameters.example.json azure/parameters.json
```

Edit `azure/parameters.json` and replace every `CHANGE_ME_*` value:

| Parameter | Description |
|---|---|
| `mysqlServerName` | Globally unique MySQL server name (e.g. `lacesta-mysql-prod`) |
| `mysqlAdminLogin` | MySQL admin username (e.g. `restadmin`) |
| `mysqlAdminPassword` | Strong MySQL admin password |
| `backendAppName` | Globally unique backend app name (e.g. `lacesta-backend-prod`) |
| `backendSecretKey` | Long random JWT secret key |
| `frontendAppName` | Globally unique frontend app name (e.g. `lacesta-frontend-prod`) |
| `frontendSecretKey` | Long random Flask session secret key |
| `dbAppPassword` | Password for the `api_user` application DB user |

> [!CAUTION]
> **Never commit** `parameters.json` to source control — it contains secrets. It is already listed in `.gitignore`.

### 2. Run the deployment script

```bash
chmod +x azure/deploy.sh
./azure/deploy.sh
```

The script performs all steps automatically:
1. Creates the Resource Group.
2. Deploys the ARM template (MySQL + App Service Plan + 2 Web Apps).
3. Initializes the database schema from `db/init.sql` and creates the `api_user`.
4. Packages and deploys the backend (ZIP deploy).
5. Packages and deploys the frontend (ZIP deploy).
6. Compiles translations on the frontend App Service.

> [!NOTE]
> MySQL provisioning takes **5–10 minutes**. The script will wait automatically.

### 3. Seed product data (optional)

After deployment, seed the product catalog from your local machine:

```bash
MYSQL_FQDN="<your-server-name>.mysql.database.azure.com"
MYSQL_ADMIN="restadmin"
MYSQL_PASS="<your-admin-password>"

for f in db/abarrotes.sql db/PROTEINAS.SQL db/panaderia.sql db/pasteleria.sql db/lacteos.sql db/pulpas.sql db/preparados.sql db/aseo-empaques.sql; do
  echo "Seeding $f..."
  mysql --host="$MYSQL_FQDN" --user="$MYSQL_ADMIN" --password="$MYSQL_PASS" --ssl-mode=REQUIRED < "$f"
done
```

### 4. First login

Open the frontend URL and log in with:
- **Username**: `admin`
- **Password**: `admin123`

> [!CAUTION]
> Change the admin password immediately after first login!

---

## Manual ARM Deployment (without the script)

If you prefer to deploy only the infrastructure manually:

```bash
# Create resource group
az group create --name lacesta-rg --location eastus2

# Deploy ARM template
az deployment group create \
  --resource-group lacesta-rg \
  --template-file azure/arm-template.json \
  --parameters @azure/parameters.json
```

Then deploy each app:

```bash
# Backend
cd backend
zip -r /tmp/backend.zip . -x "*.pyc" -x "__pycache__/*"
az webapp deploy \
  --resource-group lacesta-rg \
  --name <backendAppName> \
  --src-path /tmp/backend.zip \
  --type zip

# Frontend
cd ../frontend
zip -r /tmp/frontend.zip . -x "*.pyc" -x "__pycache__/*"
az webapp deploy \
  --resource-group lacesta-rg \
  --name <frontendAppName> \
  --src-path /tmp/frontend.zip \
  --type zip
```

---

## Environment Variables Set by the ARM Template

### Backend
| Variable | Value |
|---|---|
| `DATABASE_URL` | Full MySQL connection string (with SSL) |
| `SECRET_KEY` | JWT signing key |

### Frontend
| Variable | Value |
|---|---|
| `API_URL` | Backend URL for server-side calls |
| `PUBLIC_API_URL` | Backend URL for browser-side JS calls |
| `SECRET_KEY` | Flask session encryption key |

---

## Cleanup

To remove all Azure resources and stop billing:

```bash
az group delete --name lacesta-rg --yes --no-wait
```

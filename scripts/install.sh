#!/bin/bash
# Simbotix OTel Installation Script
# Run as: sudo -u frappe bash install.sh <site_name>

set -e

SITE_NAME=${1:-""}
BENCH_PATH="/home/frappe/frappe-bench"
OTEL_ENDPOINT="https://otel.appz.studio"
OTEL_API_KEY="57193a2d-9d50-4b81-8ffe-4b20b3e12fc6"

if [ -z "$SITE_NAME" ]; then
    echo "Usage: $0 <site_name>"
    echo "Example: $0 botz.studio"
    exit 1
fi

echo "=== Simbotix OTel Installation ==="
echo "Site: $SITE_NAME"
echo "Bench: $BENCH_PATH"
echo ""

cd "$BENCH_PATH"

# Step 1: Install OpenTelemetry Python packages
echo "[1/4] Installing OpenTelemetry packages..."
./env/bin/pip install --quiet \
    opentelemetry-api>=1.21.0 \
    opentelemetry-sdk>=1.21.0 \
    opentelemetry-exporter-otlp>=1.21.0 \
    opentelemetry-instrumentation>=0.42b0 \
    opentelemetry-instrumentation-wsgi>=0.42b0 \
    opentelemetry-instrumentation-requests>=0.42b0 \
    opentelemetry-instrumentation-redis>=0.42b0 \
    opentelemetry-instrumentation-pymysql>=0.42b0 \
    opentelemetry-instrumentation-logging>=0.42b0

echo "    Done."

# Step 2: Copy the app module
echo "[2/4] Installing simbotix_otel module..."
if [ ! -d "./apps/simbotix_otel" ]; then
    mkdir -p ./apps/simbotix_otel/simbotix_otel
fi

# The app.py will be copied separately
echo "    Done."

# Step 3: Backup current supervisor config
echo "[3/4] Backing up supervisor config..."
SUPERVISOR_CONF="/etc/supervisor/conf.d/frappe-bench.conf"
BACKUP_FILE="/etc/supervisor/conf.d/frappe-bench.conf.bak.$(date +%Y%m%d_%H%M%S)"
sudo cp "$SUPERVISOR_CONF" "$BACKUP_FILE"
echo "    Backed up to: $BACKUP_FILE"

# Step 4: Update supervisor config with OTEL environment variables
echo "[4/4] Updating supervisor config..."

# Check if OTEL vars already exist
if grep -q "OTEL_EXPORTER_OTLP_ENDPOINT" "$SUPERVISOR_CONF"; then
    echo "    OTEL environment variables already configured."
else
    # Add environment variables to the web worker section
    sudo sed -i "/\[program:frappe-bench-frappe-web\]/a environment=OTEL_EXPORTER_OTLP_ENDPOINT=\"${OTEL_ENDPOINT}\",OTEL_EXPORTER_OTLP_HEADERS=\"authorization=${OTEL_API_KEY}\",OTEL_SERVICE_NAME=\"frappe-${SITE_NAME}\",OTEL_DEPLOYMENT_ENVIRONMENT=\"production\"" "$SUPERVISOR_CONF"
    echo "    Added OTEL environment variables."
fi

# Update gunicorn command to use simbotix_otel.app:application
if grep -q "simbotix_otel.app:application" "$SUPERVISOR_CONF"; then
    echo "    Gunicorn already configured for simbotix_otel."
else
    sudo sed -i 's|frappe.app:application|simbotix_otel.app:application|g' "$SUPERVISOR_CONF"
    echo "    Updated gunicorn to use simbotix_otel.app:application"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Review the changes: sudo cat $SUPERVISOR_CONF"
echo "2. Reload supervisor: sudo supervisorctl reread && sudo supervisorctl update"
echo "3. Restart the web worker: sudo supervisorctl restart frappe-bench-frappe-web"
echo ""
echo "To verify:"
echo "- Check logs: tail -f $BENCH_PATH/logs/web.log"
echo "- View traces at: https://clickstack.appz.studio"
echo ""
echo "To rollback:"
echo "sudo cp $BACKUP_FILE $SUPERVISOR_CONF"
echo "sudo supervisorctl reread && sudo supervisorctl update"

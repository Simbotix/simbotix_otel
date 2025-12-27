# Simbotix OTel

OpenTelemetry instrumentation for Frappe/ERPNext that sends traces, metrics, and logs to ClickStack/HyperDX.

## Features

- **Traces**: HTTP requests, database queries, Redis operations
- **Metrics**: Request counts, latencies, error rates
- **Logs**: Python logging integrated with trace context

## Installation

```bash
# On your Frappe bench
cd /home/frappe/frappe-bench

# Get the app
bench get-app https://github.com/Simbotix/simbotix_otel.git

# Install on a site
bench --site your-site.com install-app simbotix_otel

# Install OpenTelemetry dependencies
./env/bin/pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp \
    opentelemetry-instrumentation opentelemetry-instrumentation-wsgi \
    opentelemetry-instrumentation-requests opentelemetry-instrumentation-redis \
    opentelemetry-instrumentation-pymysql opentelemetry-instrumentation-logging
```

## Configuration

### Option 1: Environment Variables (Recommended)

Add to your supervisor config or systemd service:

```ini
environment=OTEL_EXPORTER_OTLP_ENDPOINT="https://otel.appz.studio",OTEL_EXPORTER_OTLP_HEADERS="authorization=YOUR_API_KEY",OTEL_SERVICE_NAME="frappe-yoursite",OTEL_DEPLOYMENT_ENVIRONMENT="production"
```

### Option 2: Modify Gunicorn Command

Change the gunicorn command in supervisor to use the wrapped application:

```ini
command=/home/frappe/frappe-bench/env/bin/gunicorn -b 127.0.0.1:8000 -w 17 simbotix_otel.app:application --preload
```

### Option 3: Use opentelemetry-instrument

```ini
command=/home/frappe/frappe-bench/env/bin/opentelemetry-instrument /home/frappe/frappe-bench/env/bin/gunicorn -b 127.0.0.1:8000 -w 17 frappe.app:application --preload
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint URL | `https://otel.appz.studio` |
| `OTEL_EXPORTER_OTLP_HEADERS` | Headers (comma-separated key=value) | - |
| `OTEL_SERVICE_NAME` | Service name for traces | `frappe` |
| `OTEL_SERVICE_VERSION` | Service version | `1.0.0` |
| `OTEL_DEPLOYMENT_ENVIRONMENT` | Environment (production/staging) | `production` |

## Viewing Data

1. Open ClickStack/HyperDX at https://clickstack.appz.studio
2. Navigate to **Traces** to see request traces
3. Navigate to **Logs** to see application logs
4. Create dashboards for metrics visualization

## License

MIT

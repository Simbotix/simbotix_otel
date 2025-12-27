# Frappe OpenTelemetry Ansible Playbook

Ansible playbook to set up complete observability for Frappe/ERPNext servers.

## Features

- **Traces**: HTTP requests, database queries, Redis operations (via simbotix_otel app)
- **Application Logs**: Python logging with trace context (via simbotix_otel app)
- **File Logs**: All log files collected via FluentBit
- **Server Identification**: Public IP, hostname, server name in all telemetry

## Prerequisites

- Ansible 2.9+ on control machine
- Target server with Frappe bench installed
- SSH access with sudo privileges
- OTel collector endpoint (ClickStack/HyperDX)

## Quick Start

1. **Install Ansible** (on your local machine):
   ```bash
   pip install ansible
   ```

2. **Create inventory file**:
   ```bash
   cp inventory.example.yml inventory.yml
   ```

3. **Configure inventory.yml**:
   ```yaml
   all:
     vars:
       otel_endpoint: "https://otel.appz.studio"
       otel_api_key: "YOUR_API_KEY"
       otel_environment: "production"
     children:
       frappe_servers:
         hosts:
           my-server:
             ansible_host: 1.2.3.4
             ansible_user: ubuntu
             server_name: "frappe-prod-1"
   ```

4. **Run playbook**:
   ```bash
   ansible-playbook -i inventory.yml playbook.yml
   ```

## What Gets Installed

### simbotix_otel App
- OpenTelemetry Python SDK
- WSGI middleware for request tracing
- Site-aware service names (each Frappe site = separate service)
- Logging instrumentation with trace context

### FluentBit
- Collects all log files from bench and sites
- Adds server identification to every log entry
- Sends to OTel collector via OTLP

## Log Sources

| Log File | Tag | Service Name |
|----------|-----|--------------|
| `logs/web.log` | `frappe.web` | frappe-bench |
| `logs/worker.log` | `frappe.worker` | frappe-bench |
| `logs/frappe.log` | `frappe.frappe` | frappe-bench |
| `logs/schedule.log` | `frappe.scheduler` | frappe-bench |
| `sites/<site>/logs/*` | `site.<sitename>` | <sitename> |

## Metadata Added to All Logs

| Field | Description |
|-------|-------------|
| `server.name` | Custom server name from inventory |
| `server.hostname` | OS hostname |
| `server.ip` | Public IP address |
| `deployment.environment` | production/staging |
| `bench.path` | Path to Frappe bench |
| `log_file` | Source log file path |
| `service.name` | Site name or frappe-bench |
| `frappe.site` | Site name (for site-specific logs) |

## Advanced Usage

### Run on specific servers
```bash
ansible-playbook -i inventory.yml playbook.yml --limit my-server
```

### Only update FluentBit config
```bash
ansible-playbook -i inventory.yml playbook.yml --tags fluent-bit
```

### Check mode (dry run)
```bash
ansible-playbook -i inventory.yml playbook.yml --check
```

### Verbose output
```bash
ansible-playbook -i inventory.yml playbook.yml -vv
```

## Troubleshooting

### Check FluentBit status
```bash
sudo systemctl status fluent-bit
sudo journalctl -u fluent-bit -f
```

### Check supervisor status
```bash
sudo supervisorctl status
```

### Verify traces are being sent
```bash
curl -s https://your-site.com/api/method/frappe.ping
# Check ClickStack for new traces
```

### Manual FluentBit test
```bash
/opt/fluent-bit/bin/fluent-bit -c /etc/fluent-bit/fluent-bit.conf --dry-run
```

## Rollback

To rollback supervisor changes:
```bash
# Find backup file
ls -la /etc/supervisor/conf.d/*.bak.*

# Restore
sudo cp /etc/supervisor/conf.d/frappe-bench.conf.bak.TIMESTAMP /etc/supervisor/conf.d/frappe-bench.conf
sudo supervisorctl reread && sudo supervisorctl update
```

To disable FluentBit:
```bash
sudo systemctl stop fluent-bit
sudo systemctl disable fluent-bit
```

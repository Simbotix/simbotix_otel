"""
Simbotix OTel - OpenTelemetry instrumentation for Frappe/ERPNext

This app provides automatic instrumentation for:
- HTTP requests (via WSGI middleware)
- Database queries (PyMySQL)
- Redis operations
- Background jobs
- Logging

All telemetry is sent to ClickStack/HyperDX via OTLP protocol.
"""

__version__ = "0.1.0"

"""
OpenTelemetry WSGI Application Wrapper for Frappe

This module wraps the Frappe WSGI application with OpenTelemetry instrumentation
to collect traces, metrics, and logs.

Usage:
    Instead of using frappe.app:application directly, use:
    simbotix_otel.app:application

    Or run gunicorn with opentelemetry-instrument:
    opentelemetry-instrument gunicorn ... frappe.app:application
"""

import os
import logging

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider

# Instrumentation
from opentelemetry.instrumentation.wsgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Try to import PyMySQL instrumentation
try:
    from opentelemetry.instrumentation.pymysql import PyMySQLInstrumentor
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False


def get_otel_config():
    """Get OpenTelemetry configuration from environment variables."""
    return {
        "endpoint": os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "https://otel.appz.studio"),
        "headers": os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", ""),
        "service_name": os.environ.get("OTEL_SERVICE_NAME", "frappe"),
        "service_version": os.environ.get("OTEL_SERVICE_VERSION", "1.0.0"),
        "environment": os.environ.get("OTEL_DEPLOYMENT_ENVIRONMENT", "production"),
    }


def parse_headers(headers_str):
    """Parse OTEL headers from comma-separated key=value string."""
    if not headers_str:
        return {}
    headers = {}
    for item in headers_str.split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            headers[key.strip()] = value.strip()
    return headers


def setup_telemetry():
    """Initialize OpenTelemetry with traces, metrics, and logs."""
    config = get_otel_config()
    headers = parse_headers(config["headers"])

    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME: config["service_name"],
        SERVICE_VERSION: config["service_version"],
        DEPLOYMENT_ENVIRONMENT: config["environment"],
        "host.name": os.environ.get("HOSTNAME", "unknown"),
    })

    # === TRACES ===
    trace_exporter = OTLPSpanExporter(
        endpoint=f"{config['endpoint']}/v1/traces",
        headers=headers,
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(tracer_provider)

    # === METRICS ===
    metric_exporter = OTLPMetricExporter(
        endpoint=f"{config['endpoint']}/v1/metrics",
        headers=headers,
    )
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=60000,  # Export every 60 seconds
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # === LOGS ===
    log_exporter = OTLPLogExporter(
        endpoint=f"{config['endpoint']}/v1/logs",
        headers=headers,
    )
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)

    # Add OTEL handler to Python logging
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)

    # === INSTRUMENTATION ===
    # Instrument requests library (for external HTTP calls)
    RequestsInstrumentor().instrument()

    # Instrument Redis
    RedisInstrumentor().instrument()

    # Instrument PyMySQL (database queries)
    if HAS_PYMYSQL:
        PyMySQLInstrumentor().instrument()

    # Instrument Python logging to capture log records
    LoggingInstrumentor().instrument(set_logging_format=True)

    return tracer_provider


# Initialize telemetry on module import
_tracer_provider = None

def get_tracer_provider():
    global _tracer_provider
    if _tracer_provider is None:
        _tracer_provider = setup_telemetry()
    return _tracer_provider


# Import and wrap the Frappe application
from frappe.app import application as frappe_application

# Initialize telemetry
get_tracer_provider()

# Wrap with OpenTelemetry WSGI middleware
application = OpenTelemetryMiddleware(frappe_application)

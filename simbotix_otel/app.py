"""
OpenTelemetry WSGI Application Wrapper for Frappe

This module wraps the Frappe WSGI application with OpenTelemetry instrumentation
to collect traces, metrics, and logs with per-site service names.
"""

import os
import logging
import sys

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
        "service_version": os.environ.get("OTEL_SERVICE_VERSION", "15.91.0"),
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


# Global config and exporters (shared across sites)
_config = None
_headers = None
_tracer_providers = {}
_logger_providers = {}
_meter_provider = None
_otel_handler = None


def get_config():
    global _config, _headers
    if _config is None:
        _config = get_otel_config()
        _headers = parse_headers(_config["headers"])
    return _config, _headers


def get_site_from_host(host):
    """Extract site name from host header."""
    if not host:
        return "unknown"
    # Remove port if present
    site = host.split(":")[0]
    return site


def get_tracer_provider_for_site(site_name):
    """Get or create a tracer provider for a specific site."""
    global _tracer_providers

    if site_name in _tracer_providers:
        return _tracer_providers[site_name]

    config, headers = get_config()

    # Create resource with site-specific service name
    resource = Resource.create({
        SERVICE_NAME: site_name,
        SERVICE_VERSION: config["service_version"],
        DEPLOYMENT_ENVIRONMENT: config["environment"],
        "host.name": os.environ.get("HOSTNAME", os.uname().nodename),
        "frappe.site": site_name,
        "service.type": "frappe-web",
    })

    # Create trace exporter and provider
    trace_exporter = OTLPSpanExporter(
        endpoint=f"{config['endpoint']}/v1/traces",
        headers=headers,
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))

    _tracer_providers[site_name] = tracer_provider
    return tracer_provider


def get_logger_provider_for_site(site_name):
    """Get or create a logger provider for a specific site."""
    global _logger_providers

    if site_name in _logger_providers:
        return _logger_providers[site_name]

    config, headers = get_config()

    # Create resource with site-specific service name
    resource = Resource.create({
        SERVICE_NAME: site_name,
        SERVICE_VERSION: config["service_version"],
        DEPLOYMENT_ENVIRONMENT: config["environment"],
        "host.name": os.environ.get("HOSTNAME", os.uname().nodename),
        "frappe.site": site_name,
        "service.type": "frappe-web",
    })

    # Create log exporter and provider
    log_exporter = OTLPLogExporter(
        endpoint=f"{config['endpoint']}/v1/logs",
        headers=headers,
    )
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    _logger_providers[site_name] = logger_provider
    return logger_provider


def setup_global_telemetry():
    """Initialize global telemetry components (metrics, instrumentation)."""
    global _meter_provider, _otel_handler

    config, headers = get_config()

    # Create a default resource for metrics (aggregated across sites)
    resource = Resource.create({
        SERVICE_NAME: "frappe-web",
        SERVICE_VERSION: config["service_version"],
        DEPLOYMENT_ENVIRONMENT: config["environment"],
        "host.name": os.environ.get("HOSTNAME", os.uname().nodename),
    })

    # === METRICS (global) ===
    metric_exporter = OTLPMetricExporter(
        endpoint=f"{config['endpoint']}/v1/metrics",
        headers=headers,
    )
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=30000,
    )
    _meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(_meter_provider)

    # === DEFAULT TRACER (for non-request operations) ===
    default_tracer_provider = get_tracer_provider_for_site("frappe-web")
    trace.set_tracer_provider(default_tracer_provider)

    # === DEFAULT LOGGER ===
    default_logger_provider = get_logger_provider_for_site("frappe-web")
    set_logger_provider(default_logger_provider)

    # Create OTEL logging handler
    _otel_handler = LoggingHandler(level=logging.INFO, logger_provider=default_logger_provider)

    # Add OTEL handler to loggers
    for logger_name in [None, "frappe", "gunicorn.error", "gunicorn.access", "werkzeug"]:
        logger = logging.getLogger(logger_name)
        logger.addHandler(_otel_handler)
        if logger_name is None:
            logger.setLevel(logging.INFO)

    # === INSTRUMENTATION ===
    RequestsInstrumentor().instrument()
    RedisInstrumentor().instrument()
    if HAS_PYMYSQL:
        PyMySQLInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=True)


class SiteAwareOTelMiddleware:
    """
    Custom WSGI middleware that sets the service name based on the request host.
    """

    def __init__(self, app):
        self.app = app
        self._wsgi_middlewares = {}

    def _get_middleware_for_site(self, site_name):
        """Get or create WSGI middleware for a specific site."""
        if site_name not in self._wsgi_middlewares:
            tracer_provider = get_tracer_provider_for_site(site_name)
            self._wsgi_middlewares[site_name] = OpenTelemetryMiddleware(
                self.app,
                tracer_provider=tracer_provider,
            )
        return self._wsgi_middlewares[site_name]

    def __call__(self, environ, start_response):
        # Extract site from HTTP_HOST
        host = environ.get("HTTP_HOST", "")
        site_name = get_site_from_host(host)

        # Get site-specific middleware
        middleware = self._get_middleware_for_site(site_name)

        # Add site to environ for Frappe to use
        environ["OTEL_SITE_NAME"] = site_name

        return middleware(environ, start_response)


# Initialize global telemetry on module import
setup_global_telemetry()

# Import the Frappe application
from frappe.app import application as frappe_application

# Wrap with site-aware middleware
application = SiteAwareOTelMiddleware(frappe_application)

# Log initialization
logging.getLogger("simbotix_otel").info("OpenTelemetry site-aware instrumentation initialized for Frappe")

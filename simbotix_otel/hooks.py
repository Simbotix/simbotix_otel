app_name = "simbotix_otel"
app_title = "Simbotix OTel"
app_publisher = "Simbotix"
app_description = "OpenTelemetry instrumentation for Frappe/ERPNext"
app_email = "rajesh@simbotix.com"
app_license = "MIT"

# Apps
required_apps = ["frappe"]

# App includes
app_include_css = []
app_include_js = []

# The app.py file contains the WSGI middleware wrapper
# It will be used when gunicorn is started with opentelemetry-instrument

# Boot session hooks - add trace context to session
# boot_session = "simbotix_otel.boot.boot_session"

# Document events for tracing
# doc_events = {
#     "*": {
#         "before_insert": "simbotix_otel.tracing.trace_doc_event",
#         "after_insert": "simbotix_otel.tracing.trace_doc_event",
#         "before_save": "simbotix_otel.tracing.trace_doc_event",
#         "after_save": "simbotix_otel.tracing.trace_doc_event",
#     }
# }

# Scheduler events tracing
# scheduler_events = {
#     "all": ["simbotix_otel.tracing.trace_scheduler_event"]
# }

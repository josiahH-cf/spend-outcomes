"""Review-only provider configuration proposal. Never reads or changes settings."""


def make_export_plan(port=4318, entrypoint='cli'):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('port must be between 1 and 65535')
    if entrypoint not in ('cli', 'vscode', 'desktop'):
        raise ValueError('entrypoint must be cli, vscode or desktop')
    environment = {
        'CLAUDE_CODE_ENABLE_TELEMETRY': '1',
        'OTEL_METRICS_EXPORTER': 'otlp',
        'OTEL_EXPORTER_OTLP_METRICS_PROTOCOL': 'http/json',
        'OTEL_EXPORTER_OTLP_METRICS_ENDPOINT': 'http://127.0.0.1:' + str(port) + '/v1/metrics',
        'OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE': 'delta',
        'OTEL_LOGS_EXPORTER': 'none', 'OTEL_TRACES_EXPORTER': 'none',
        'OTEL_LOG_ASSISTANT_RESPONSES': '0',
        'OTEL_METRICS_INCLUDE_SESSION_ID': 'true', 'OTEL_METRICS_INCLUDE_ENTRYPOINT': 'true',
        'OTEL_METRICS_INCLUDE_VERSION': 'true', 'OTEL_METRICS_INCLUDE_ACCOUNT_UUID': 'false',
        'OTEL_METRICS_INCLUDE_REPOSITORY': 'false', 'OTEL_METRIC_EXPORT_INTERVAL': '10000'}
    absent = ['OTEL_LOG_USER_PROMPTS', 'OTEL_LOG_TOOL_DETAILS', 'OTEL_LOG_TOOL_CONTENT',
        'OTEL_LOG_MANAGED_SETTINGS', 'OTEL_LOG_RAW_API_BODIES', 'CLAUDE_CODE_ENHANCED_TELEMETRY_BETA',
        'ENABLE_ENHANCED_TELEMETRY_BETA', 'ENABLE_BETA_TRACING_DETAILED', 'BETA_TRACING_ENDPOINT',
        'OTEL_EXPORTER_OTLP_HEADERS', 'OTEL_EXPORTER_OTLP_METRICS_HEADERS',
        'OTEL_EXPORTER_OTLP_COMPRESSION', 'OTEL_EXPORTER_OTLP_METRICS_COMPRESSION']
    surfaces = {'cli': 'An explicitly approved isolated launch environment for the installed CLI.',
        'vscode': 'The approved VS Code claudeCode.environmentVariables scope, separately reviewed.',
        'desktop': 'The applicable Desktop Code-tab managed/launcher configuration, reviewed by its owner.'}
    return {'contract': 'cherry-meter-export-plan-v1', 'status': 'review_required', 'entrypoint': entrypoint,
        'proposed_environment': environment, 'must_be_absent_from_effective_configuration': absent,
        'settings_read': False, 'settings_changed': False, 'applied': False,
        'configuration_surface': surfaces[entrypoint],
        'requirements': [
            'Inspect existing configuration only with permission; never print or copy secret header values.',
            'Review inherited generic and metric-specific headers and otelHeadersHelper before redirecting metrics.',
            'Absence means absent from the effective client configuration; shell deletion alone may allow a settings fallback.',
            'Managed or launcher telemetry destinations may be locked. Do not bypass or overwrite policy.',
            'Do not apply this plan automatically or merge it over an existing instrumentation destination.',
            'A repository-local settings file cannot enable or change the export destination.',
            'Default project attribution remains unassigned unless explicit workspace/session bindings are established.',
            'These variables are a proposal, not proof of provider/GUI/IDE delivery. Controlled qualification is required.'],
        'source': 'https://code.claude.com/docs/en/monitoring-usage'}

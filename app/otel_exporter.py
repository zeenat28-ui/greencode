"""CNCF OpenTelemetry (OTLP/HTTP v1 JSON) Carbon & FinOps Metric Exporter.

Serializes GreenCode Software Carbon Intensity (ISO/IEC 21031 / GSF SCI),
hardware energy telemetry, and GHG Protocol Scope 2/3 metrics into the standard
OpenTelemetry `ExportMetricsServiceRequest` JSON payload (`resourceMetrics ->
scopeMetrics -> metrics`) for ingestion by Grafana Cloud, Datadog, New Relic,
and OpenTelemetry Collectors (`http://localhost:4318/v1/metrics`).
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional
import urllib.request
import json

from app import energy_sensors, sci


def _otel_attr(key: str, value: Any) -> Dict[str, Any]:
    """Encode a key-value attribute into the OTLP JSON AnyValue representation."""
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    return {"key": key, "value": {"stringValue": str(value)}}


def _otel_gauge_metric(
    name: str,
    description: str,
    unit: str,
    value: float,
    timestamp_unix_nano: str,
    attributes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a single OTLP v1 Gauge metric entry."""
    return {
        "name": name,
        "description": description,
        "unit": unit,
        "gauge": {
            "dataPoints": [
                {
                    "timeUnixNano": timestamp_unix_nano,
                    "asDouble": round(float(value), 8),
                    "attributes": attributes,
                }
            ]
        },
    }


def _build_metric_list(
    sci_res: Any,
    energy_joules: float,
    grid_intensity_gco2_kwh: float,
    green_score: float,
    now_ns: str,
    dp_attrs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Assemble the 6 canonical GreenCode OTLP gauge metrics."""
    specs = [
        ("greencode.sci.gco2e_per_unit", "Software Carbon Intensity (ISO/IEC 21031 / GSF SCI) per functional unit", "g{CO2e}/{unit}", sci_res.sci_gco2_per_functional_unit),
        ("greencode.energy.joules", "Workload energy consumption in Joules", "J", energy_joules),
        ("greencode.grid.carbon_intensity", "Electricity grid carbon intensity in gCO2e/kWh", "g{CO2e}/kWh", grid_intensity_gco2_kwh),
        ("greencode.audit.green_score", "Repository Green Score (0-100)", "1", green_score),
        ("greencode.scope2.operational_gco2e", "GHG Protocol Scope 2 operational emissions in gCO2e", "g{CO2e}", sci_res.operational_gco2),
        ("greencode.scope3.embodied_gco2e", "GHG Protocol Scope 3 hardware embodied emissions in gCO2e", "g{CO2e}", sci_res.embodied_gco2),
    ]
    return [
        _otel_gauge_metric(name, desc, unit, val, now_ns, dp_attrs)
        for name, desc, unit, val in specs
    ]


def build_otlp_metrics_payload(
    *,
    service_name: str = "greencode-auditor",
    repository: str = "zeenat28-ui/greencode",
    green_score: float = 100.0,
    energy_joules: float = 25.0,
    duration_seconds: float = 1.0,
    functional_unit: float = 1.0,
    grid_intensity_gco2_kwh: float = 210.0,
    zone: str = "IE",
    measurement_method: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct a compliant OTLP/HTTP v1 `ExportMetricsServiceRequest` JSON dict."""
    caps = energy_sensors.probe_capabilities()
    method = measurement_method or str(caps.get("best_available", "model"))
    is_hw = energy_sensors.is_hardware_method(method)
    sci_res = sci.compute_sci(
        energy_joules=max(0.0, float(energy_joules)),
        duration_seconds=max(0.001, float(duration_seconds)),
        carbon_intensity_gco2_per_kwh=max(0.0, float(grid_intensity_gco2_kwh)),
        functional_unit=max(0.0001, float(functional_unit)),
        measurement_method=method,
    )
    now_ns = str(int(time.time() * 1_000_000_000))
    resource_attrs = [
        _otel_attr("service.name", service_name),
        _otel_attr("service.version", "2.1.0"),
        _otel_attr("vcs.repository.name", repository),
        _otel_attr("cloud.region", zone),
        _otel_attr("greencode.measurement.method", method),
        _otel_attr("greencode.measurement.is_hardware", is_hw),
    ]
    dp_attrs = [
        _otel_attr("grid.zone", zone),
        _otel_attr("measurement.method", method),
        _otel_attr("measurement.is_hardware", is_hw),
    ]
    metrics = _build_metric_list(
        sci_res, energy_joules, grid_intensity_gco2_kwh, green_score, now_ns, dp_attrs
    )
    return {
        "resourceMetrics": [
            {
                "resource": {"attributes": resource_attrs},
                "scopeMetrics": [
                    {
                        "scope": {"name": "io.greencode.telemetry.sci", "version": "2.1.0"},
                        "metrics": metrics,
                    }
                ],
            }
        ]
    }


def export_otlp_metrics(
    payload: Dict[str, Any],
    endpoint: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout_sec: float = 5.0,
) -> Dict[str, Any]:
    """Push an OTLP JSON metrics payload to an OTLP/HTTP collector endpoint if configured."""
    target_url = (
        endpoint
        or os.environ.get("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "").strip()
    )
    if not target_url:
        return {
            "exported": False,
            "mode": "dry_run_serialized",
            "payload": payload,
        }

    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(
        target_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=req_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310
            return {
                "exported": 200 <= resp.status < 300,
                "status_code": resp.status,
                "endpoint": target_url,
                "payload": payload,
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "exported": False,
            "endpoint": target_url,
            "error": f"{type(exc).__name__}: {exc}",
            "payload": payload,
        }


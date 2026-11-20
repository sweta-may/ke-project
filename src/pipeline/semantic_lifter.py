"""
Semantic Lifter Layer
Transforms raw sensor streaming telemetry into enriched semantic observations
grounded in the static knowledge graph ontology.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum
import time

class SeverityState(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

@dataclass
class RawSensorReading:
    sensor_id: str
    value: float
    timestamp: float

@dataclass
class SemanticObservation:
    sensor_id: str
    metric: str
    value: float
    unit: str
    state: SeverityState
    component_id: str
    machine_id: str
    timestamp: float
    warning_threshold: float
    critical_threshold: float

class SemanticLifter:
    """Lifts raw sensor telemetry into ontologically grounded semantic observations."""

    def __init__(self, kg_store):
        self.kg = kg_store

    def lift(self, reading: RawSensorReading) -> Optional[SemanticObservation]:
        sensor_meta = self.kg.sensors.get(reading.sensor_id)
        if not sensor_meta:
            return None

        # Determine severity state based on metric type
        # For coolant pressure: lower is dangerous; for temp/vib/current: higher is dangerous
        if sensor_meta.metric_name == "coolant_pressure":
            if reading.value <= sensor_meta.critical_threshold:
                state = SeverityState.CRITICAL
            elif reading.value <= sensor_meta.warning_threshold:
                state = SeverityState.WARNING
            else:
                state = SeverityState.NORMAL
        else:
            if reading.value >= sensor_meta.critical_threshold:
                state = SeverityState.CRITICAL
            elif reading.value >= sensor_meta.warning_threshold:
                state = SeverityState.WARNING
            else:
                state = SeverityState.NORMAL

        return SemanticObservation(
            sensor_id=reading.sensor_id,
            metric=sensor_meta.metric_name,
            value=reading.value,
            unit=sensor_meta.unit,
            state=state,
            component_id=sensor_meta.component_id,
            machine_id=sensor_meta.machine_id,
            timestamp=reading.timestamp,
            warning_threshold=sensor_meta.warning_threshold,
            critical_threshold=sensor_meta.critical_threshold
        )

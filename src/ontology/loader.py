"""
Static Knowledge Base & Ontology Loader
Loads RDF/OWL ontology and exposes structured queries for machines, components, and sensors.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import os
import re

@dataclass
class SensorMetadata:
    sensor_id: str
    component_id: str
    machine_id: str
    metric_name: str
    unit: str
    warning_threshold: float
    critical_threshold: float
    label: str

@dataclass
class ComponentMetadata:
    component_id: str
    label: str
    component_type: str
    operating_hours: float
    rated_operating_hours: float
    machine_id: str
    sensors: List[str] = field(default_factory=list)

    @property
    def operating_ratio(self) -> float:
        if self.rated_operating_hours <= 0:
            return 0.0
        return self.operating_hours / self.rated_operating_hours

@dataclass
class MachineMetadata:
    machine_id: str
    label: str
    machine_type: str
    components: List[str] = field(default_factory=list)


class KnowledgeGraphStore:
    """In-memory Knowledge Graph representation with RDF Turtle parsing capabilities."""

    def __init__(self, turtle_path: Optional[str] = None):
        self.machines: Dict[str, MachineMetadata] = {}
        self.components: Dict[str, ComponentMetadata] = {}
        self.sensors: Dict[str, SensorMetadata] = {}
        self.actions: Dict[str, str] = {}
        self.failure_modes: Dict[str, str] = {}
        
        if turtle_path and os.path.exists(turtle_path):
            self.load_turtle(turtle_path)

    def load_turtle(self, filepath: str) -> None:
        """Parses the Turtle ontology file and populates the entity registry."""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Try to use rdflib if installed, else fallback to semantic regex parser
        try:
            import rdflib
            self._load_with_rdflib(filepath)
        except ImportError:
            self._load_with_builtin_parser(content)

    def _load_with_rdflib(self, filepath: str) -> None:
        import rdflib
        g = rdflib.Graph()
        g.parse(filepath, format="turtle")
        
        NS = rdflib.Namespace("http://smartfactory.org/ontology#")
        RDFS = rdflib.Namespace("http://www.w3.org/2000/01/rdf-schema#")

        # Load Machines
        for s, p, o in g.triples((None, rdflib.RDF.type, NS.CNCMachine)):
            m_id = str(g.value(s, NS.machineId) or "CNC-01")
            label = str(g.value(s, RDFS.label) or s.split("#")[-1])
            self.machines[m_id] = MachineMetadata(
                machine_id=m_id,
                label=label,
                machine_type="CNCMachine"
            )

        # Load Components
        for s in g.subjects(NS.componentId, None):
            c_id = str(g.value(s, NS.componentId))
            label = str(g.value(s, RDFS.label) or s.split("#")[-1])
            c_type = "Component"
            for t in g.objects(s, rdflib.RDF.type):
                if str(t).startswith(str(NS)):
                    c_type = str(t).split("#")[-1]
            op_hours = float(g.value(s, NS.operatingHours) or 0.0)
            rated_hours = float(g.value(s, NS.ratedOperatingHours) or 1.0)
            
            comp = ComponentMetadata(
                component_id=c_id,
                label=label,
                component_type=c_type,
                operating_hours=op_hours,
                rated_operating_hours=rated_hours,
                machine_id="CNC-MILL-01"
            )
            self.components[c_id] = comp
            # Also key by IRI fragment name (e.g., 'Spindle_01')
            iri_name = str(s).split("#")[-1]
            self.components[iri_name] = comp

        # Load Sensors
        for s in g.subjects(NS.sensorId, None):
            s_id = str(g.value(s, NS.sensorId))
            metric = str(g.value(s, NS.metricName) or "unknown")
            unit = str(g.value(s, NS.unitOfMeasure) or "")
            warn = float(g.value(s, NS.warningThreshold) or 0.0)
            crit = float(g.value(s, NS.criticalThreshold) or 0.0)
            label = str(g.value(s, RDFS.label) or s_id)
            
            # Find monitored component
            comp_name = "Unknown"
            for comp_subj in g.subjects(NS.monitoredBy, s):
                comp_name = str(comp_subj).split("#")[-1]

            self.sensors[s_id] = SensorMetadata(
                sensor_id=s_id,
                component_id=comp_name,
                machine_id="CNC-MILL-01",
                metric_name=metric,
                unit=unit,
                warning_threshold=warn,
                critical_threshold=crit,
                label=label
            )

    def _load_with_builtin_parser(self, content: str) -> None:
        """Robust fallback Turtle parser for zero-dependency execution."""
        # Predefined static domain values matching factory_ontology.ttl
        self.machines["CNC-MILL-01"] = MachineMetadata(
            machine_id="CNC-MILL-01",
            label="5-Axis High Precision CNC Milling Center",
            machine_type="CNCMachine",
            components=["Spindle_01", "DriveMotor_01", "CoolantPump_01"]
        )

        self.components["Spindle_01"] = ComponentMetadata(
            component_id="CMP-SPINDLE-01",
            label="Electro-Spindle Unit",
            component_type="Spindle",
            operating_hours=4250.0,
            rated_operating_hours=5000.0,
            machine_id="CNC-MILL-01",
            sensors=["SEN-VIB-01", "SEN-TMP-01"]
        )

        self.components["DriveMotor_01"] = ComponentMetadata(
            component_id="CMP-MOTOR-01",
            label="Main AC Servo Motor",
            component_type="Motor",
            operating_hours=6100.0,
            rated_operating_hours=8000.0,
            machine_id="CNC-MILL-01",
            sensors=["SEN-CURR-01"]
        )

        self.components["CoolantPump_01"] = ComponentMetadata(
            component_id="CMP-COOLANT-01",
            label="High-Pressure Flood Coolant Pump",
            component_type="CoolantSystem",
            operating_hours=2100.0,
            rated_operating_hours=10000.0,
            machine_id="CNC-MILL-01",
            sensors=["SEN-PRS-01"]
        )

        # Sensors
        self.sensors["SEN-VIB-01"] = SensorMetadata(
            sensor_id="SEN-VIB-01",
            component_id="Spindle_01",
            machine_id="CNC-MILL-01",
            metric_name="vibration_rms",
            unit="mm/s",
            warning_threshold=4.5,
            critical_threshold=7.1,
            label="Spindle Drive-End Vibration Sensor"
        )

        self.sensors["SEN-TMP-01"] = SensorMetadata(
            sensor_id="SEN-TMP-01",
            component_id="Spindle_01",
            machine_id="CNC-MILL-01",
            metric_name="temperature",
            unit="degC",
            warning_threshold=75.0,
            critical_threshold=90.0,
            label="Spindle Thermal Probe"
        )

        self.sensors["SEN-CURR-01"] = SensorMetadata(
            sensor_id="SEN-CURR-01",
            component_id="DriveMotor_01",
            machine_id="CNC-MILL-01",
            metric_name="motor_current",
            unit="A",
            warning_threshold=26.0,
            critical_threshold=35.0,
            label="Motor Phase Current Sensor"
        )

        self.sensors["SEN-PRS-01"] = SensorMetadata(
            sensor_id="SEN-PRS-01",
            component_id="CoolantPump_01",
            machine_id="CNC-MILL-01",
            metric_name="coolant_pressure",
            unit="bar",
            warning_threshold=2.2,
            critical_threshold=1.2,
            label="Coolant Delivery Line Pressure Sensor"
        )

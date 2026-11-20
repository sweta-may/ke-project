"""
Streamlit Interactive Dashboard for Smart Factory Knowledge Engineering
Run with: streamlit run src/app/streamlit_app.py
"""
import os
import sys
import time

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    import streamlit as st
    import pandas as pd
except ImportError:
    print("Streamlit not installed. Please run: pip install streamlit")
    sys.exit(0)

from src.ontology.loader import KnowledgeGraphStore
from src.pipeline.semantic_lifter import SemanticLifter
from src.rules.rule_evaluator import ExpertRuleEngine
from src.simulator.sensor_stream import SmartFactorySimulator

st.set_page_config(page_title="Smart Factory KE Dashboard", layout="wide", page_icon="🏭")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ONTOLOGY_PATH = os.path.join(BASE_DIR, "data", "factory_ontology.ttl")
RULES_PATH = os.path.join(BASE_DIR, "data", "expert_rules.json")

@st.cache_resource
def load_ke_system():
    kg = KnowledgeGraphStore(ONTOLOGY_PATH)
    lifter = SemanticLifter(kg)
    engine = ExpertRuleEngine(RULES_PATH, kg)
    simulator = SmartFactorySimulator()
    return kg, lifter, engine, simulator

kg, lifter, engine, simulator = load_ke_system()

st.title("🏭 Smart Factory Knowledge Engineering Platform")
st.markdown("**Dynamic Sensor Stream Reasoning & Static Ontology Integration**")

# Sidebar Controls
st.sidebar.header("Simulation Settings")
scenario = st.sidebar.selectbox(
    "Choose Failure Scenario:",
    ["normal", "bearing_wear", "coolant_loss", "motor_overload"],
    format_func=lambda x: {
        "normal": "Normal Baseline Run",
        "bearing_wear": "Bearing Wear & Thermal Fatigue",
        "coolant_loss": "Coolant Pressure Loss",
        "motor_overload": "Motor Overload Spike"
    }[x]
)
ticks = st.sidebar.slider("Number of Simulation Steps", min_value=3, max_value=15, value=6)
start_sim = st.sidebar.button("Run Simulation Stream", type="primary")

# Static Knowledge Base Inspection
with st.expander("🔍 Inspect Static Knowledge Graph (OWL/RDF Ontology & Assets)", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Machines & Components")
        for m_id, m in kg.machines.items():
            st.markdown(f"**Machine:** `{m.machine_id}` ({m.label})")
            for c_id in m.components:
                c = kg.components.get(c_id)
                if c:
                    st.write(f"- Component: `{c.label}` | Operating Hours: {c.operating_hours}/{c.rated_operating_hours} hrs ({c.operating_ratio*100:.1f}%)")
    with col2:
        st.subheader("Configured Sensors & Rules")
        for s_id, s in kg.sensors.items():
            st.write(f"- `{s.sensor_id}` ({s.label}) | Metric: {s.metric_name} | Warn: {s.warning_threshold}, Crit: {s.critical_threshold}")

if start_sim:
    st.subheader(f"Telemetry & Rule Inferences: {scenario.replace('_', ' ').title()}")
    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    metrics_placeholder = st.empty()
    alerts_placeholder = st.empty()

    active_observations = {}
    history = []

    for step, batch in enumerate(simulator.generate_scenario_ticks(scenario=scenario, ticks=ticks), 1):
        progress_bar.progress(step / ticks)
        for reading in batch:
            obs = lifter.lift(reading)
            if obs:
                active_observations[obs.sensor_id] = obs
                history.append({
                    "step": step,
                    "sensor": obs.sensor_id,
                    "metric": obs.metric,
                    "value": obs.value,
                    "state": obs.state.value
                })

        # Run inference
        inferences = engine.evaluate(active_observations)

        # Render current metrics
        with metrics_placeholder.container():
            cols = st.columns(4)
            for i, (s_id, obs) in enumerate(active_observations.items()):
                delta_str = f"Threshold: {obs.warning_threshold}"
                cols[i % 4].metric(
                    label=f"{obs.sensor_id} ({obs.metric})",
                    value=f"{obs.value} {obs.unit}",
                    delta=f"State: {obs.state.value}",
                    delta_color="normal" if obs.state.value == "NORMAL" else "inverse"
                )

        # Render Inferences
        with alerts_placeholder.container():
            if inferences:
                st.error(f"⚠️ {len(inferences)} Active Alert(s) Fired by Expert Rule Engine")
                for inf in inferences:
                    st.markdown(f"### [{inf.severity}] {inf.rule_name}")
                    st.write(f"**Diagnosis:** {inf.explanation}")
                    st.info(f"**Prescribed Action:** `{inf.recommended_action}`")
                    st.json(inf.triggering_evidence)
            else:
                st.success("✅ System Status: Healthy - All sensor streams satisfy operational ontology rules.")

        time.sleep(0.5)

    st.success("Simulation Run Complete!")

"""
End-to-End Demo Runner
Executes the Smart Factory Knowledge Engineering Pipeline:
Dynamic Sensor Streaming -> Semantic Lifting -> Knowledge Graph Contextualization -> Expert Rule Inference
"""
import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ontology.loader import KnowledgeGraphStore
from src.pipeline.semantic_lifter import SemanticLifter
from src.rules.rule_evaluator import ExpertRuleEngine
from src.simulator.sensor_stream import SmartFactorySimulator

def run_pipeline_demo():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ontology_path = os.path.join(base_dir, "data", "factory_ontology.ttl")
    rules_path = os.path.join(base_dir, "data", "expert_rules.json")

    print("=" * 80)
    print("   SMART FACTORY KNOWLEDGE ENGINEERING SYSTEM (DYNAMIC + STATIC REASONING)   ")
    print("=" * 80)

    # 1. Load Static Knowledge Graph & Expert Rules
    print("\n[Phase 1] Loading Static Domain Knowledge & Expert Heuristics...")
    kg = KnowledgeGraphStore(ontology_path)
    rule_engine = ExpertRuleEngine(rules_path, kg)
    lifter = SemanticLifter(kg)

    print(f" -> Machines Registered: {len(kg.machines)}")
    for m_id, m in kg.machines.items():
        print(f"    * {m.label} (ID: {m.machine_id})")
        for c_id in m.components:
            comp = kg.components.get(c_id)
            if comp:
                print(f"      - Component: {comp.label} ({comp.component_type}) | Hours: {comp.operating_hours}/{comp.rated_operating_hours} hrs ({comp.operating_ratio*100:.1f}% used)")

    print(f" -> Sensors Configured: {len(kg.sensors)}")
    for s_id, s in kg.sensors.items():
        print(f"    * [{s.sensor_id}] {s.label} -> Metric: {s.metric_name} ({s.unit}) | Warn: {s.warning_threshold}, Crit: {s.critical_threshold}")

    print(f" -> Expert Rules Loaded: {len(rule_engine.rules)}")
    for r in rule_engine.rules:
        print(f"    * {r['id']}: {r['name']}")

    simulator = SmartFactorySimulator()

    # 2. Run Test Scenarios
    scenarios = [
        ("Normal Baseline Run", "normal", 3),
        ("Bearing Wear & Degradation Scenario", "bearing_wear", 6),
        ("Coolant Line Failure Scenario", "coolant_loss", 5)
    ]

    for title, scenario_key, ticks in scenarios:
        print("\n" + "=" * 80)
        print(f" SIMULATING SCENARIO: {title}")
        print("=" * 80)

        active_observations = {}

        for step, batch in enumerate(simulator.generate_scenario_ticks(scenario=scenario_key, ticks=ticks), 1):
            print(f"\n--- [Timestep T+{step}s] ---")
            
            # Step A: Semantic Lifting of raw readings
            for reading in batch:
                obs = lifter.lift(reading)
                if obs:
                    active_observations[obs.sensor_id] = obs
                    status_flag = f"[{obs.state.value}]"
                    print(f"  Telemetry: {obs.sensor_id} ({obs.metric}) = {obs.value} {obs.unit} {status_flag}")

            # Step B: Knowledge Fusion & Rule Inference
            inferences = rule_engine.evaluate(active_observations)

            if inferences:
                print(f"\n  >>> INFERENCE ENGINE FIRED ({len(inferences)} Active Alert(s)) <<<")
                for inf in inferences:
                    print(f"  [SEVERITY: {inf.severity}] Rule Triggered: {inf.rule_name} ({inf.rule_id})")
                    print(f"   Target Component : {inf.target_component}")
                    print(f"   Inferred Failure : {inf.failure_mode}")
                    print(f"   Diagnosis        : {inf.explanation}")
                    print(f"   Action Prescribed: {inf.recommended_action}")
                    print(f"   Grounded Evidence: {inf.triggering_evidence}")
            else:
                print("  System State: HEALTHY / STABLE (No expert rules violated)")

    print("\n" + "=" * 80)
    print("DEMO EXECUTION COMPLETE: Dynamic sensor knowledge successfully combined with static domain knowledge.")
    print("=" * 80)

if __name__ == "__main__":
    run_pipeline_demo()

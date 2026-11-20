"""
Expert Rule Engine / Reasoner
Evaluates multi-condition expert heuristic rules over dynamic observations and static domain knowledge.
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.pipeline.semantic_lifter import SemanticObservation, SeverityState

@dataclass
class DiagnosticInference:
    rule_id: str
    rule_name: str
    severity: str
    failure_mode: str
    target_component: str
    explanation: str
    recommended_action: str
    triggering_evidence: List[Dict[str, Any]] = field(default_factory=list)


class ExpertRuleEngine:
    """Inference engine evaluating expert rules against fused static & dynamic facts."""

    def __init__(self, rules_file_path: str, kg_store):
        self.kg = kg_store
        self.rules = self._load_rules(rules_file_path)

    def _load_rules(self, filepath: str) -> List[Dict[str, Any]]:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("rules", [])

    def evaluate(self, active_observations: Dict[str, SemanticObservation]) -> List[DiagnosticInference]:
        """
        Evaluates active dynamic observations alongside static knowledge graph context.
        :param active_observations: Dict mapping sensor_id -> latest SemanticObservation
        :return: List of DiagnosticInference objects for fired rules
        """
        inferences = []

        for rule in self.rules:
            conditions = rule.get("conditions", {})
            target_comp = conditions.get("target_component")
            dynamic_conds = conditions.get("dynamic_conditions", [])
            static_conds = conditions.get("static_conditions", [])

            rule_satisfied = True
            evidence = []

            # 1. Evaluate Dynamic Conditions
            for cond in dynamic_conds:
                s_id = cond["sensor_id"]
                obs = active_observations.get(s_id)
                if not obs:
                    rule_satisfied = False
                    break

                target_state = cond.get("state_check")
                if target_state == "CRITICAL" and obs.state != SeverityState.CRITICAL:
                    rule_satisfied = False
                    break
                elif target_state == "WARNING" and obs.state not in [SeverityState.WARNING, SeverityState.CRITICAL]:
                    rule_satisfied = False
                    break

                evidence.append({
                    "sensor_id": s_id,
                    "metric": obs.metric,
                    "value": obs.value,
                    "unit": obs.unit,
                    "state": obs.state.value
                })

            if not rule_satisfied:
                continue

            # 2. Evaluate Static Domain Conditions from Knowledge Graph
            comp_meta = self.kg.components.get(target_comp)
            for s_cond in static_conds:
                prop = s_cond.get("property")
                op = s_cond.get("operator")
                expected_val = s_cond.get("value")

                if prop == "operating_ratio" and comp_meta:
                    actual_ratio = comp_meta.operating_ratio
                    if op == ">=" and not (actual_ratio >= expected_val):
                        rule_satisfied = False
                        break
                    evidence.append({
                        "property": "operating_ratio",
                        "actual": round(actual_ratio, 3),
                        "threshold": expected_val
                    })

            # 3. If all conditions met, record the inference conclusion
            if rule_satisfied:
                conclusion = rule.get("conclusion", {})
                inferences.append(DiagnosticInference(
                    rule_id=rule.get("id", "UNKNOWN"),
                    rule_name=rule.get("name", "Unnamed Rule"),
                    severity=conclusion.get("severity", "WARNING"),
                    failure_mode=conclusion.get("failure_mode", "UnknownFailure"),
                    target_component=target_comp,
                    explanation=conclusion.get("explanation", ""),
                    recommended_action=conclusion.get("action", "Inspect"),
                    triggering_evidence=evidence
                ))

        return inferences

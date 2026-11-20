"""
Unit and Integration Tests for Knowledge Fusion & Expert Rules
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ontology.loader import KnowledgeGraphStore
from src.pipeline.semantic_lifter import SemanticLifter, RawSensorReading, SeverityState
from src.rules.rule_evaluator import ExpertRuleEngine

class TestKnowledgeEngineeringPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.ontology_path = os.path.join(base_dir, "data", "factory_ontology.ttl")
        cls.rules_path = os.path.join(base_dir, "data", "expert_rules.json")
        cls.kg = KnowledgeGraphStore(cls.ontology_path)
        cls.lifter = SemanticLifter(cls.kg)
        cls.engine = ExpertRuleEngine(cls.rules_path, cls.kg)

    def test_ontology_loading(self):
        self.assertIn("CNC-MILL-01", self.kg.machines)
        self.assertIn("Spindle_01", self.kg.components)
        self.assertIn("SEN-VIB-01", self.kg.sensors)
        spindle = self.kg.components["Spindle_01"]
        self.assertGreater(spindle.operating_ratio, 0.8)

    def test_semantic_lifting_normal(self):
        reading = RawSensorReading("SEN-VIB-01", 2.0, 1000.0)
        obs = self.lifter.lift(reading)
        self.assertIsNotNone(obs)
        self.assertEqual(obs.state, SeverityState.NORMAL)

    def test_semantic_lifting_warning_and_critical(self):
        warn_reading = RawSensorReading("SEN-VIB-01", 5.0, 1000.0)
        obs_warn = self.lifter.lift(warn_reading)
        self.assertEqual(obs_warn.state, SeverityState.WARNING)

        crit_reading = RawSensorReading("SEN-VIB-01", 8.0, 1000.0)
        obs_crit = self.lifter.lift(crit_reading)
        self.assertEqual(obs_crit.state, SeverityState.CRITICAL)

    def test_coolant_starvation_rule_trigger(self):
        # Coolant pressure low + Temperature high
        obs_press = self.lifter.lift(RawSensorReading("SEN-PRS-01", 1.8, 1000.0)) # WARNING
        obs_temp = self.lifter.lift(RawSensorReading("SEN-TMP-01", 78.0, 1000.0))  # WARNING

        active = {
            "SEN-PRS-01": obs_press,
            "SEN-TMP-01": obs_temp
        }
        inferences = self.engine.evaluate(active)
        rule_ids = [inf.rule_id for inf in inferences]
        self.assertIn("RULE_002_COOLANT_STARVATION", rule_ids)

    def test_thermal_runaway_rule_trigger(self):
        obs_temp = self.lifter.lift(RawSensorReading("SEN-TMP-01", 93.0, 1000.0)) # CRITICAL
        active = {"SEN-TMP-01": obs_temp}
        inferences = self.engine.evaluate(active)
        rule_ids = [inf.rule_id for inf in inferences]
        self.assertIn("RULE_003_THERMAL_RUNAWAY", rule_ids)
        self.assertEqual(inferences[0].recommended_action, "Action_EmergencyShutdown")

if __name__ == "__main__":
    unittest.main()

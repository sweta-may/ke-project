"""
Smart Factory Sensor Telemetry Simulator
Generates synthetic real-time telemetry streams simulating both normal operations
and complex industrial degradation failure modes.
"""
import time
import random
from typing import Generator, List
from src.pipeline.semantic_lifter import RawSensorReading

class SmartFactorySimulator:
    """Generates continuous raw sensor data packets."""

    def __init__(self):
        # Baseline healthy parameters
        self.spindle_vib = 2.1      # mm/s RMS (Healthy: 1.5 - 3.0)
        self.spindle_temp = 48.0    # degC (Healthy: 40 - 60)
        self.motor_curr = 18.5      # Amps (Healthy: 15 - 22)
        self.coolant_press = 4.5    # bar (Healthy: 3.5 - 5.0)

    def generate_scenario_ticks(self, scenario: str = "normal", ticks: int = 10) -> Generator[List[RawSensorReading], None, None]:
        """
        Yields batches of sensor readings representing factory timesteps.
        Scenarios: 'normal', 'bearing_wear', 'coolant_loss', 'motor_overload'
        """
        for t in range(ticks):
            ts = time.time() + t

            if scenario == "normal":
                vib = self.spindle_vib + random.uniform(-0.2, 0.2)
                temp = self.spindle_temp + random.uniform(-0.5, 0.5)
                curr = self.motor_curr + random.uniform(-0.5, 0.5)
                press = self.coolant_press + random.uniform(-0.1, 0.1)

            elif scenario == "bearing_wear":
                # Gradual degradation of bearing: high vibration followed by heat
                vib = 4.2 + (t * 0.4) + random.uniform(-0.1, 0.2) # cross 4.5 -> 7.1
                temp = 72.0 + (t * 1.5) + random.uniform(-0.3, 0.3) # cross 75.0
                curr = self.motor_curr + random.uniform(-0.5, 0.5)
                press = self.coolant_press + random.uniform(-0.1, 0.1)

            elif scenario == "coolant_loss":
                # Rapid pressure loss leading to thermal overheat
                press = max(0.5, self.coolant_press - (t * 0.5)) # falls below 2.2 and 1.2
                temp = 60.0 + (t * 3.5) # escalates rapidly past 75 and 90
                vib = self.spindle_vib + random.uniform(-0.2, 0.2)
                curr = self.motor_curr + random.uniform(-0.5, 0.5)

            elif scenario == "motor_overload":
                # Current spike
                curr = 24.0 + (t * 1.5) + random.uniform(-0.2, 0.2) # cross 26.0 A
                vib = self.spindle_vib + random.uniform(-0.1, 0.1)
                temp = self.spindle_temp + random.uniform(-0.5, 0.5)
                press = self.coolant_press + random.uniform(-0.1, 0.1)

            else:
                raise ValueError(f"Unknown scenario: {scenario}")

            yield [
                RawSensorReading(sensor_id="SEN-VIB-01", value=round(vib, 2), timestamp=ts),
                RawSensorReading(sensor_id="SEN-TMP-01", value=round(temp, 2), timestamp=ts),
                RawSensorReading(sensor_id="SEN-CURR-01", value=round(curr, 2), timestamp=ts),
                RawSensorReading(sensor_id="SEN-PRS-01", value=round(press, 2), timestamp=ts)
            ]

"""
FastAPI Server for Smart Factory Knowledge Engineering Dashboard
Provides REST and WebSocket endpoints for streaming sensor telemetry,
knowledge graph inspection, and real-time expert rule inference.
"""
import os
import sys
import asyncio
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.ontology.loader import KnowledgeGraphStore
from src.pipeline.semantic_lifter import SemanticLifter, RawSensorReading
from src.rules.rule_evaluator import ExpertRuleEngine
from src.simulator.sensor_stream import SmartFactorySimulator

app = FastAPI(title="Smart Factory Knowledge Engineering Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Knowledge Engineering Context
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ONTOLOGY_PATH = os.path.join(BASE_DIR, "data", "factory_ontology.ttl")
RULES_PATH = os.path.join(BASE_DIR, "data", "expert_rules.json")

kg = KnowledgeGraphStore(ONTOLOGY_PATH)
lifter = SemanticLifter(kg)
rule_engine = ExpertRuleEngine(RULES_PATH, kg)
simulator = SmartFactorySimulator()

# Current simulation state
simulation_state = {
    "scenario": "normal",
    "step": 0,
    "active_observations": {}
}

class StepRequest(BaseModel):
    scenario: str = "normal"
    reset: bool = False

@app.get("/api/ontology")
def get_ontology():
    """Returns static knowledge graph topology and metadata."""
    return {
        "machines": {
            m_id: {
                "id": m.machine_id,
                "label": m.label,
                "type": m.machine_type,
                "components": m.components
            }
            for m_id, m in kg.machines.items()
        },
        "components": {
            c_id: {
                "id": c.component_id,
                "label": c.label,
                "type": c.component_type,
                "operating_hours": c.operating_hours,
                "rated_operating_hours": c.rated_operating_hours,
                "operating_ratio": round(c.operating_ratio, 3),
                "sensors": c.sensors
            }
            for c_id, c in kg.components.items()
        },
        "sensors": {
            s_id: {
                "id": s.sensor_id,
                "component": s.component_id,
                "metric": s.metric_name,
                "unit": s.unit,
                "warning_threshold": s.warning_threshold,
                "critical_threshold": s.critical_threshold,
                "label": s.label
            }
            for s_id, s in kg.sensors.items()
        },
        "rules": rule_engine.rules
    }

@app.post("/api/step")
def advance_simulation_step(req: StepRequest):
    """Advances telemetry simulation by 1 timestep and runs the inference engine."""
    if req.reset or req.scenario != simulation_state["scenario"]:
        simulation_state["scenario"] = req.scenario
        simulation_state["step"] = 0
        simulation_state["active_observations"] = {}

    simulation_state["step"] += 1
    step_num = simulation_state["step"]

    # Generate one tick batch
    generator = simulator.generate_scenario_ticks(scenario=simulation_state["scenario"], ticks=step_num)
    current_batch = []
    for batch in generator:
        current_batch = batch

    # Run Semantic Lifting
    lifted_data = []
    for reading in current_batch:
        obs = lifter.lift(reading)
        if obs:
            simulation_state["active_observations"][obs.sensor_id] = obs
            lifted_data.append({
                "sensor_id": obs.sensor_id,
                "metric": obs.metric,
                "value": obs.value,
                "unit": obs.unit,
                "state": obs.state.value,
                "component_id": obs.component_id,
                "warning_threshold": obs.warning_threshold,
                "critical_threshold": obs.critical_threshold
            })

    # Run Expert Rule Inferences
    inferences = rule_engine.evaluate(simulation_state["active_observations"])
    formatted_inferences = [
        {
            "rule_id": inf.rule_id,
            "rule_name": inf.rule_name,
            "severity": inf.severity,
            "failure_mode": inf.failure_mode,
            "target_component": inf.target_component,
            "diagnosis": inf.explanation,
            "recommended_action": inf.recommended_action,
            "evidence": inf.triggering_evidence
        }
        for inf in inferences
    ]

    return {
        "step": step_num,
        "scenario": simulation_state["scenario"],
        "observations": lifted_data,
        "inferences": formatted_inferences
    }

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serves the complete single-page interactive Smart Factory Knowledge Engineering Dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Factory | Knowledge Engineering Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .glow-red { box-shadow: 0 0 15px rgba(239, 68, 68, 0.4); }
        .glow-amber { box-shadow: 0 0 15px rgba(245, 158, 11, 0.4); }
        .glow-green { box-shadow: 0 0 15px rgba(16, 185, 129, 0.3); }
        body { background-color: #0b1120; }
    </style>
</head>
<body class="text-slate-100 font-sans antialiased min-h-screen">
    <!-- Header -->
    <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50 px-6 py-4 flex flex-wrap justify-between items-center">
        <div class="flex items-center gap-3">
            <div class="p-2 bg-indigo-600/30 border border-indigo-500 rounded-lg text-indigo-400">
                <i class="fa-solid fa-industry text-xl"></i>
            </div>
            <div>
                <h1 class="text-lg font-bold text-white tracking-wide">Smart Factory Knowledge Engineering</h1>
                <p class="text-xs text-slate-400">Dynamic Sensor Stream Reasoning & Static Ontology Integration</p>
            </div>
        </div>

        <!-- Controls -->
        <div class="flex items-center gap-3 mt-3 sm:mt-0">
            <div class="flex items-center gap-2 bg-slate-800 p-1.5 rounded-lg border border-slate-700">
                <label class="text-xs text-slate-400 pl-2">Scenario:</label>
                <select id="scenario-select" class="bg-slate-900 text-xs text-white border border-slate-700 rounded px-2 py-1 outline-none">
                    <option value="normal">Normal Baseline Run</option>
                    <option value="bearing_wear">Bearing Wear & Thermal Fatigue</option>
                    <option value="coolant_loss">Coolant Pressure Loss</option>
                    <option value="motor_overload">Motor Overload / Current Spike</option>
                </select>
            </div>
            <button id="step-btn" class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition">
                <i class="fa-solid fa-forward-step"></i> Step
            </button>
            <button id="play-btn" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition">
                <i class="fa-solid fa-play" id="play-icon"></i> <span id="play-text">Auto Run</span>
            </button>
            <button id="reset-btn" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold rounded-lg text-slate-300 border border-slate-700 transition">
                <i class="fa-solid fa-rotate-left"></i> Reset
            </button>
        </div>
    </header>

    <main class="p-6 max-w-7xl mx-auto space-y-6">
        <!-- Top Status Bar -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                <div>
                    <span class="text-xs text-slate-400 uppercase font-medium">System State</span>
                    <h3 id="stat-system-state" class="text-lg font-bold text-emerald-400">HEALTHY</h3>
                </div>
                <div id="stat-state-icon" class="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <i class="fa-solid fa-circle-check"></i>
                </div>
            </div>

            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                <div>
                    <span class="text-xs text-slate-400 uppercase font-medium">Machine Asset</span>
                    <h3 class="text-lg font-bold text-white">CNC-MILL-01</h3>
                </div>
                <div class="w-10 h-10 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
                    <i class="fa-solid fa-gear"></i>
                </div>
            </div>

            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                <div>
                    <span class="text-xs text-slate-400 uppercase font-medium">Simulation Clock</span>
                    <h3 id="stat-timestep" class="text-lg font-bold text-indigo-400">T + 0s</h3>
                </div>
                <div class="w-10 h-10 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                    <i class="fa-solid fa-clock"></i>
                </div>
            </div>

            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                <div>
                    <span class="text-xs text-slate-400 uppercase font-medium">Active Rule Inferences</span>
                    <h3 id="stat-alert-count" class="text-lg font-bold text-slate-300">0 Active</h3>
                </div>
                <div id="stat-alert-icon" class="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400">
                    <i class="fa-solid fa-shield"></i>
                </div>
            </div>
        </div>

        <!-- Telemetry Gauges / Charts Section -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <!-- Vibration -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-xs font-semibold text-slate-300">Spindle Vibration RMS</span>
                    <span id="badge-vib" class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">NORMAL</span>
                </div>
                <div class="flex items-baseline gap-2 mb-3">
                    <span id="val-vib" class="text-2xl font-black text-white">--</span>
                    <span class="text-xs text-slate-400">mm/s (Warn: 4.5 | Crit: 7.1)</span>
                </div>
                <div class="h-28">
                    <canvas id="chart-vib"></canvas>
                </div>
            </div>

            <!-- Temperature -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-xs font-semibold text-slate-300">Spindle Temperature</span>
                    <span id="badge-temp" class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">NORMAL</span>
                </div>
                <div class="flex items-baseline gap-2 mb-3">
                    <span id="val-temp" class="text-2xl font-black text-white">--</span>
                    <span class="text-xs text-slate-400">°C (Warn: 75 | Crit: 90)</span>
                </div>
                <div class="h-28">
                    <canvas id="chart-temp"></canvas>
                </div>
            </div>

            <!-- Coolant Pressure -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-xs font-semibold text-slate-300">Coolant Pressure</span>
                    <span id="badge-press" class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">NORMAL</span>
                </div>
                <div class="flex items-baseline gap-2 mb-3">
                    <span id="val-press" class="text-2xl font-black text-white">--</span>
                    <span class="text-xs text-slate-400">bar (Warn &lt; 2.2 | Crit &lt; 1.2)</span>
                </div>
                <div class="h-28">
                    <canvas id="chart-press"></canvas>
                </div>
            </div>

            <!-- Motor Current -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-xs font-semibold text-slate-300">Main Motor Current</span>
                    <span id="badge-curr" class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">NORMAL</span>
                </div>
                <div class="flex items-baseline gap-2 mb-3">
                    <span id="val-curr" class="text-2xl font-black text-white">--</span>
                    <span class="text-xs text-slate-400">A (Warn: 26 | Crit: 35)</span>
                </div>
                <div class="h-28">
                    <canvas id="chart-curr"></canvas>
                </div>
            </div>
        </div>

        <!-- Main Middle Section: Diagnostic Inferences & Static Knowledge Context -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Left: Live Inference & Explainability Engine (2 Cols) -->
            <div class="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col">
                <div class="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                    <div class="flex items-center gap-2">
                        <i class="fa-solid fa-brain text-indigo-400"></i>
                        <h2 class="text-sm font-bold uppercase tracking-wider text-white">Active Rule Inferences & Root-Cause Diagnosis</h2>
                    </div>
                    <span class="text-xs text-slate-400">Real-Time Knowledge Fusion Engine</span>
                </div>

                <div id="inferences-container" class="space-y-3 flex-1 overflow-y-auto max-h-[360px] pr-1">
                    <div class="p-6 text-center border border-dashed border-slate-800 rounded-lg text-slate-500">
                        <i class="fa-solid fa-circle-check text-3xl mb-2 text-emerald-500/50"></i>
                        <p class="text-sm">All operations are within safe threshold parameters.</p>
                        <p class="text-xs text-slate-600 mt-1">Dynamic telemetry satisfies all static domain constraints.</p>
                    </div>
                </div>
            </div>

            <!-- Right: Static Ontology Asset Context (1 Col) -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col">
                <div class="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                    <div class="flex items-center gap-2">
                        <i class="fa-solid fa-diagram-project text-blue-400"></i>
                        <h2 class="text-sm font-bold uppercase tracking-wider text-white">Static Knowledge Graph</h2>
                    </div>
                    <span class="text-xs text-slate-400">OWL/RDF</span>
                </div>

                <div class="space-y-3 text-xs flex-1 overflow-y-auto max-h-[360px]">
                    <!-- Machine Node -->
                    <div class="p-3 bg-slate-800/60 rounded-lg border border-slate-700/60">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-white"><i class="fa-solid fa-industry text-blue-400 mr-1.5"></i> CNC-MILL-01</span>
                            <span class="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded">CNCMachine</span>
                        </div>
                        <p class="text-slate-400 text-[11px] mt-1">5-Axis High Precision CNC Milling Center</p>
                    </div>

                    <!-- Spindle Component -->
                    <div class="p-3 bg-slate-800/40 rounded-lg border border-slate-700/40 ml-3">
                        <div class="flex items-center justify-between">
                            <span class="font-semibold text-slate-200"><i class="fa-solid fa-cog text-indigo-400 mr-1"></i> Spindle_01</span>
                            <span class="text-[10px] text-amber-400 font-mono">85% Lifetime Used</span>
                        </div>
                        <div class="w-full bg-slate-700 h-1.5 rounded-full mt-2 overflow-hidden">
                            <div class="bg-amber-500 h-full rounded-full" style="width: 85%;"></div>
                        </div>
                        <div class="flex justify-between text-[10px] text-slate-400 mt-1">
                            <span>Hours: 4,250 hrs</span>
                            <span>Rated: 5,000 hrs</span>
                        </div>
                        <div class="mt-2 text-[10px] text-slate-400">
                            Sensors: <span class="text-indigo-300 font-mono">SEN-VIB-01</span>, <span class="text-indigo-300 font-mono">SEN-TMP-01</span>
                        </div>
                    </div>

                    <!-- Drive Motor Component -->
                    <div class="p-3 bg-slate-800/40 rounded-lg border border-slate-700/40 ml-3">
                        <div class="flex items-center justify-between">
                            <span class="font-semibold text-slate-200"><i class="fa-solid fa-bolt text-amber-400 mr-1"></i> DriveMotor_01</span>
                            <span class="text-[10px] text-slate-400 font-mono">76% Lifetime Used</span>
                        </div>
                        <div class="w-full bg-slate-700 h-1.5 rounded-full mt-2 overflow-hidden">
                            <div class="bg-blue-500 h-full rounded-full" style="width: 76.2%;"></div>
                        </div>
                        <div class="flex justify-between text-[10px] text-slate-400 mt-1">
                            <span>Hours: 6,100 hrs</span>
                            <span>Rated: 8,000 hrs</span>
                        </div>
                    </div>

                    <!-- Coolant Pump Component -->
                    <div class="p-3 bg-slate-800/40 rounded-lg border border-slate-700/40 ml-3">
                        <div class="flex items-center justify-between">
                            <span class="font-semibold text-slate-200"><i class="fa-solid fa-droplet text-cyan-400 mr-1"></i> CoolantPump_01</span>
                            <span class="text-[10px] text-slate-400 font-mono">21% Lifetime Used</span>
                        </div>
                        <div class="w-full bg-slate-700 h-1.5 rounded-full mt-2 overflow-hidden">
                            <div class="bg-emerald-500 h-full rounded-full" style="width: 21%;"></div>
                        </div>
                        <div class="flex justify-between text-[10px] text-slate-400 mt-1">
                            <span>Hours: 2,100 hrs</span>
                            <span>Rated: 10,000 hrs</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        // Chart initialization helpers
        function createSensorChart(canvasId, label, color, min, max) {
            const ctx = document.getElementById(canvasId).getContext('2d');
            return new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: label,
                        data: [],
                        borderColor: color,
                        backgroundColor: color + '22',
                        borderWidth: 2,
                        pointRadius: 2,
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: false },
                        y: {
                            min: min,
                            max: max,
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#64748b', font: { size: 9 } }
                        }
                    }
                }
            });
        }

        const chartVib = createSensorChart('chart-vib', 'Vibration', '#f59e0b', 0, 10);
        const chartTemp = createSensorChart('chart-temp', 'Temperature', '#ef4444', 30, 110);
        const chartPress = createSensorChart('chart-press', 'Pressure', '#06b6d4', 0, 6);
        const chartCurr = createSensorChart('chart-curr', 'Current', '#a855f7', 10, 40);

        function updateChart(chart, val, maxPoints = 15) {
            if (chart.data.labels.length >= maxPoints) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }
            chart.data.labels.push('');
            chart.data.datasets[0].data.push(val);
            chart.update();
        }

        function resetCharts() {
            [chartVib, chartTemp, chartPress, chartCurr].forEach(c => {
                c.data.labels = [];
                c.data.datasets[0].data = [];
                c.update();
            });
        }

        let autoRunInterval = null;

        async function stepSimulation(reset = false) {
            const scenario = document.getElementById('scenario-select').value;
            const res = await fetch('/api/step', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenario, reset })
            });
            const data = await res.json();
            renderStep(data);
        }

        function renderStep(data) {
            document.getElementById('stat-timestep').innerText = `T + ${data.step}s`;

            // Update Sensor Values & Charts
            data.observations.forEach(obs => {
                if (obs.metric === 'vibration_rms') {
                    document.getElementById('val-vib').innerText = obs.value;
                    updateBadge('badge-vib', obs.state);
                    updateChart(chartVib, obs.value);
                } else if (obs.metric === 'temperature') {
                    document.getElementById('val-temp').innerText = obs.value;
                    updateBadge('badge-temp', obs.state);
                    updateChart(chartTemp, obs.value);
                } else if (obs.metric === 'coolant_pressure') {
                    document.getElementById('val-press').innerText = obs.value;
                    updateBadge('badge-press', obs.state);
                    updateChart(chartPress, obs.value);
                } else if (obs.metric === 'motor_current') {
                    document.getElementById('val-curr').innerText = obs.value;
                    updateBadge('badge-curr', obs.state);
                    updateChart(chartCurr, obs.value);
                }
            });

            // Update Inferences
            const container = document.getElementById('inferences-container');
            const alertCount = data.inferences.length;
            document.getElementById('stat-alert-count').innerText = `${alertCount} Active`;

            if (alertCount === 0) {
                document.getElementById('stat-system-state').innerText = 'HEALTHY';
                document.getElementById('stat-system-state').className = 'text-lg font-bold text-emerald-400';
                document.getElementById('stat-state-icon').className = 'w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400';
                document.getElementById('stat-state-icon').innerHTML = '<i class="fa-solid fa-circle-check"></i>';

                container.innerHTML = `
                    <div class="p-6 text-center border border-dashed border-slate-800 rounded-lg text-slate-500">
                        <i class="fa-solid fa-circle-check text-3xl mb-2 text-emerald-500/50"></i>
                        <p class="text-sm">All operations are within safe threshold parameters.</p>
                        <p class="text-xs text-slate-600 mt-1">Dynamic telemetry satisfies all static domain constraints.</p>
                    </div>
                `;
            } else {
                let maxSeverity = 'WARNING';
                container.innerHTML = '';

                data.inferences.forEach(inf => {
                    if (inf.severity === 'CRITICAL' || inf.severity === 'EMERGENCY') {
                        maxSeverity = inf.severity;
                    }
                    const badgeColor = inf.severity === 'EMERGENCY' ? 'bg-red-600 text-white' :
                                       inf.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' :
                                       'bg-amber-500/20 text-amber-400 border border-amber-500/40';

                    const card = document.createElement('div');
                    card.className = 'p-4 rounded-lg bg-slate-800/80 border border-slate-700 space-y-2';
                    card.innerHTML = `
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-sm text-white">${inf.rule_name}</span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeColor}">${inf.severity}</span>
                        </div>
                        <p class="text-xs text-slate-300">${inf.diagnosis}</p>
                        <div class="p-2.5 bg-slate-900/90 rounded border border-slate-700/80 flex items-center gap-2">
                            <i class="fa-solid fa-triangle-exclamation text-amber-400 text-xs"></i>
                            <span class="text-xs font-semibold text-amber-200">Prescribed Action:</span>
                            <span class="text-xs text-slate-300">${inf.recommended_action}</span>
                        </div>
                        <div class="text-[11px] text-slate-400 flex flex-wrap gap-2 pt-1 border-t border-slate-700/50">
                            <span class="font-semibold text-indigo-300">Grounded Evidence:</span>
                            ${inf.evidence.map(e => e.metric ? `<span class="bg-slate-900 px-1.5 py-0.5 rounded text-slate-300">${e.metric}=${e.value} (${e.state})</span>` : `<span class="bg-slate-900 px-1.5 py-0.5 rounded text-slate-300">${e.property}=${e.actual}</span>`).join('')}
                        </div>
                    `;
                    container.appendChild(card);
                });

                document.getElementById('stat-system-state').innerText = maxSeverity;
                document.getElementById('stat-system-state').className = `text-lg font-bold ${maxSeverity === 'EMERGENCY' ? 'text-red-500' : 'text-rose-400'}`;
                document.getElementById('stat-state-icon').className = 'w-10 h-10 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400';
                document.getElementById('stat-state-icon').innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
            }
        }

        function updateBadge(id, state) {
            const el = document.getElementById(id);
            el.innerText = state;
            if (state === 'CRITICAL') {
                el.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40 glow-red';
            } else if (state === 'WARNING') {
                el.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40 glow-amber';
            } else {
                el.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 glow-green';
            }
        }

        // Event Listeners
        document.getElementById('step-btn').addEventListener('click', () => stepSimulation(false));
        document.getElementById('scenario-select').addEventListener('change', () => {
            resetCharts();
            stepSimulation(true);
        });

        document.getElementById('reset-btn').addEventListener('click', () => {
            resetCharts();
            stepSimulation(true);
        });

        document.getElementById('play-btn').addEventListener('click', () => {
            if (autoRunInterval) {
                clearInterval(autoRunInterval);
                autoRunInterval = null;
                document.getElementById('play-icon').className = 'fa-solid fa-play';
                document.getElementById('play-text').innerText = 'Auto Run';
            } else {
                autoRunInterval = setInterval(() => stepSimulation(false), 1200);
                document.getElementById('play-icon').className = 'fa-solid fa-pause';
                document.getElementById('play-text').innerText = 'Pause';
            }
        });

        // Initial Step
        stepSimulation(true);
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.app.server:app", host="127.0.0.1", port=8000, reload=False)

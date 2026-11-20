# Smart Factory Knowledge Engineering (KE) System

> **A hybrid Knowledge Engineering system combining dynamic real-time sensor streams with static domain ontology and expert diagnostic rules.**

---

## 📌 Problem Formulation
In an industrial smart factory:
- **Dynamic Sensor Knowledge:** Arrives at high frequency (vibration RMS, temperature, current, coolant pressure). It is quantitative, noisy, and transient.
- **Static Domain Knowledge:** Factory asset topologies, component relationships, physical specifications, lifetime statistics, and expert diagnostic heuristic rules.

### How Does the System Combine Them?
The system uses **Semantic Lifting** and **Contextual Stream Reasoning**:
1. **Semantic Lifting:** Ingests raw continuous numerical sensor readings and classifies them into qualitative semantic states (`NORMAL`, `WARNING`, `CRITICAL`) using grounded thresholds.
2. **Knowledge Graph Contextualization:** Dynamically attaches the lifted sensor observations to the static OWL/RDF ontology (e.g., mapping `SEN-VIB-01` to `Spindle_01` on machine `CNC-MILL-01`, inspecting historical operating hours and rated life).
3. **Multi-Condition Expert Rule Engine:** Forward-chains rules that evaluate conjunctions of dynamic sensor states with static machine properties (e.g., *If Spindle Vibration is WARNING and Temperature is WARNING and Component Operating Hours exceed 80% of rated life $\rightarrow$ Infer Critical Bearing Fatigue*).
4. **Explainable Action Prescription:** Outputs structured failure modes, root-cause explanations, and standard operating procedure (SOP) maintenance actions.

---

## 🏗️ Architecture

```
[IoT Sensor Streams] (Vibration, Temp, Pressure, Current)
         │
         ▼
[Semantic Lifter] ──────────► [Dynamic Observations: State & Metrics]
                                      │
                                      ▼
[Static Ontology (OWL/RDF)] ──► [Contextual Fusion Engine]
  - Asset Hierarchy                   │
  - Component Specs                   │
  - Operating Hours                   ▼
[Expert Rules (JSON/SWRL)] ───► [Rule Inference Engine]
                                      │
                                      ▼
                           [Diagnostic Inferences]
                           - Root Cause Analysis
                           - Severity Assessment
                           - Prescribed SOP Action
```

---

## 📁 Repository Structure

```text
ke-project/
├── data/
│   ├── factory_ontology.ttl    # W3C OWL/RDF Turtle static factory domain ontology
│   └── expert_rules.json       # Codified multi-condition expert heuristic rules
├── src/
│   ├── ontology/
│   │   └── loader.py           # Knowledge Graph loader and query interface
│   ├── pipeline/
│   │   └── semantic_lifter.py  # Lifts raw metrics -> semantic observations
│   ├── rules/
│   │   └── rule_evaluator.py   # Multi-condition forward-chaining rule engine
│   ├── simulator/
│   │   └── sensor_stream.py    # Industrial telemetry stream generator (failure scenarios)
│   └── demo_runner.py          # End-to-end executable demonstration
├── tests/
│   └── test_scenarios.py       # Automated test suite
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- (Optional) `rdflib` and `pydantic`:
  ```bash
  pip install -r requirements.txt
  ```
  *(Note: The system contains built-in zero-dependency fallbacks so it runs immediately out of the box).*

### 2. Run the Interactive Web Dashboard (FastAPI - Zero Extra Dependencies)
The project comes with a built-in interactive web dashboard powered by FastAPI, Chart.js, and Tailwind CSS:
```bash
python -m uvicorn src.app.server:app --port 8000
```
Then open your browser at **`http://127.0.0.1:8000`** to:
- Select and trigger real-time failure scenarios (*Normal, Bearing Degradation, Coolant Loss, Motor Overload*).
- View live streaming sensor telemetry charts with threshold indicators.
- Inspect the static Knowledge Graph asset hierarchy and component lifetimes.
- Watch the expert rule inference engine fire live alerts with grounded root-cause diagnoses and prescribed maintenance actions.

### 3. (Optional) Run with Streamlit
If you have Streamlit installed (`pip install streamlit`):
```bash
streamlit run src/app/streamlit_app.py
```

### 4. Run the Terminal Demo Pipeline
```bash
python src/demo_runner.py
```

### 5. Run Automated Tests
```bash
python tests/test_scenarios.py
```

---

## 📅 Phased Development Roadmap

- [x] **Phase 1: Domain Knowledge Modeling & Expert Rules**
  - Formulated `data/factory_ontology.ttl` (OWL/RDF T-Box & A-Box).
  - Codified rules in `data/expert_rules.json`.
- [x] **Phase 2: Dynamic Sensor Pipeline & Stream Simulator**
  - Implemented `src/simulator/sensor_stream.py` with multi-scenario failure modes.
- [x] **Phase 3: Semantic Lifting & Contextual Fusion**
  - Implemented `src/pipeline/semantic_lifter.py` mapping raw time-series data to ontology entities.
- [x] **Phase 4: Reasoning & Rule Execution Engine**
  - Implemented `src/rules/rule_evaluator.py` evaluating static + dynamic conjunctions.
- [x] **Phase 5: Interactive Dashboard & Web Interface**
  - Implemented real-time interactive UI in `src/app/server.py` and `src/app/streamlit_app.py`.

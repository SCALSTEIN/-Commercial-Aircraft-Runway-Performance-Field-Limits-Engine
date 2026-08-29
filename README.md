# 🛫 Commercial Aircraft Runway Performance & Field Limits Engine

An end-to-end Flight Operations Engineering dispatch software platform designed to compute Performance-Limited Maximum Takeoff Weight (PLMTOW / RTOW), evaluate 2nd-segment OEI climb gradients, and calculate regulatory V-speeds ($V_1, V_R, V_2$) and factored landing distances.

[![Live Demo](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://scalstein-runway-performance.streamlit.app/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 1. Operational Context & Problem Statement
Every commercial flight departure is legally governed by **Performance-Limited Takeoff Weight (PLMTOW)** requirements (ICAO Annex 6, FAR 25 / CS-25). 

An aircraft cannot simply depart at its structural maximum weight; it must be audited against multi-variable physical constraints:
* **Field Length Limits:** Balanced field length ensuring the aircraft can accelerate to $V_1$, suffer an engine failure, and either abort within Accelerate-Stop Distance Available (ASDA) or continue climb to 35 ft within Takeoff Distance Available (TODA).
* **Climb Gradient Limits:** One-Engine Inoperative (OEI) second-segment climb gradient minimums ($\ge 2.4\%$) to clear takeoff flight path obstacles.
* **Tire Speed & Brake Energy Limits:** Maximum kinetic energy absorption during high-speed rejected takeoffs.
* **Atmospheric Density Degradation:** "Hot and High" airport conditions (elevated pressure and density altitudes) that reduce jet engine thrust output and aerodynamic wing lift.

This system provides a full interactive dispatch interface calculating real-time governing weight restrictions and regulatory speeds.

---

## 🧮 2. Mathematical Formulation & Performance Aerodynamics

### A. Atmospheric Density & ISA Deviations
$$\text{ISA Temperature at Elevation } (T_{\text{ISA}}) = 15.0 - \left(1.98 \cdot \frac{h_{\text{elev}}}{1000}\right)$$

$$\text{Pressure Altitude } (H_p) = h_{\text{elev}} + (1013.25 - QNH) \cdot 27.0$$

$$\text{Density Altitude } (H_d) = H_p + 120.0 \cdot (\text{OAT} - T_{\text{ISA}})$$

### B. Runway Aerodynamic Wind Vectors
Given surface wind velocity $V_{\text{wind}}$, wind direction $\theta_{\text{wind}}$, and magnetic runway heading $\theta_{\text{rwy}}$:

$$\text{Headwind Component } (W_h) = V_{\text{wind}} \cdot \cos(\theta_{\text{wind}} - \theta_{\text{rwy}})$$
$$\text{Crosswind Component } (W_c) = V_{\text{wind}} \cdot |\sin(\theta_{\text{wind}} - \theta_{\text{rwy}})|$$

### C. Regulated Takeoff Weight (RTOW) Optimization
$$\text{RTOW} = \min\left( \text{MTOW}_{\text{field}}, \; \text{MTOW}_{\text{climb}}, \; \text{MTOW}_{\text{tire}}, \; \text{MTOW}_{\text{brake}}, \; \text{MTOW}_{\text{structural}} \right)$$

*Where:*
* $\text{MTOW}_{\text{field}} = f(\text{TORA}, \text{ASDA}, H_d, \text{Slope}, W_h, \text{Flap})$
* $\text{MTOW}_{\text{climb}} = f(\gamma_{\text{OEI}} \ge 2.4\%, \text{Bleeds}, \Delta\text{ISA})$

### D. Factored Regulatory Landing Distance (LDA)
$$\text{Required Landing Distance (Dry)} = \frac{\text{Actual Landing Distance}}{0.60} = \text{ALD} \cdot 1.67$$
$$\text{Required Landing Distance (Wet)} = \text{Required Dry Distance} \cdot 1.15 = \text{ALD} \cdot 1.92$$

---

## 🏗️ 3. Repository Architecture

```text
runway-performance-takeoff-landing/
├── app.py                     # Self-contained Streamlit performance solver & UI
├── requirements.txt           # Production dependencies
├── .gitignore
├── README.md
└── tests/
    └── test_performance.py    # Automated pytest verification test suite

# Clone the repository
git clone [https://github.com/scalstein/runway-performance-takeoff-landing.git](https://github.com/scalstein/runway-performance-takeoff-landing.git)
cd runway-performance-takeoff-landing

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run automated test suite
pytest tests/

# Launch the Streamlit application
streamlit run app.py

📊 5. Dashboard Capabilities
Active Regulatory Limit Attribution: Horizontal comparative bar chart highlighting the exact active operational bottleneck (Field Length, 2nd Segment Climb, or Tire Speed).
TORA vs Required TOD Field Margins: Visual runway distance breakdown comparing accelerate-stop and takeoff run against physical paved tarmac.
Takeoff Decision Speeds Engine: Calculates calibrated $V_1, V_R, V_2$ speeds and landing $V_{\text{REF}}$.
Factored Landing Distance Dispatch Audit: Automatically verifies compliance with the mandatory $60\%$ commercial dispatch landing rule on dry/wet runways

👨‍💻 Engineering Author
Pascal Ambogo Mudimba

Flight Operations Engineering & Aviation Data Systems

GitHub: @scalstein

Streamlit Hub: share.streamlit.io/user/scalstein

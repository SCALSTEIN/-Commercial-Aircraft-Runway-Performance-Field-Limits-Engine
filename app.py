"""
Runway Performance & Maximum Takeoff/Landing Weight (MTOW/MLDW) Calculator
Author: Pascal Ambogo Mudimba (@scalstein)
Flight Operations Engineering & Dispatch Regulatory Suite
"""

import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Runway Performance & Field Limits Calculator | Flight Ops",
    layout="wide",
    page_icon="🛫"
)

# ---------------------------------------------------------
# 1. AIRPORT RUNWAY & AIRCRAFT AERO/ENGINE MASTER DATA
# ---------------------------------------------------------

AIRPORTS_DATA = {
    "HKJK": {
        "name": "Nairobi (Jomo Kenyatta Intl)",
        "elevation_ft": 5330,
        "runways": {
            "06": {"tora_m": 4117, "toda_m": 4117, "asda_m": 4117, "lda_m": 4117, "slope_pct": 0.35, "heading_deg": 57},
            "24": {"tora_m": 4117, "toda_m": 4117, "asda_m": 4117, "lda_m": 4117, "slope_pct": -0.35, "heading_deg": 237}
        }
    },
    "HKMO": {
        "name": "Mombasa (Moi Intl)",
        "elevation_ft": 200,
        "runways": {
            "03": {"tora_m": 3350, "toda_m": 3350, "asda_m": 3350, "lda_m": 3350, "slope_pct": 0.10, "heading_deg": 33},
            "21": {"tora_m": 3350, "toda_m": 3350, "asda_m": 3350, "lda_m": 3350, "slope_pct": -0.10, "heading_deg": 213}
        }
    },
    "HKEL": {
        "name": "Eldoret Intl (High Elevation Hot & High)",
        "elevation_ft": 6940,
        "runways": {
            "08": {"tora_m": 3475, "toda_m": 3475, "asda_m": 3475, "lda_m": 3475, "slope_pct": 0.40, "heading_deg": 82},
            "26": {"tora_m": 3475, "toda_m": 3475, "asda_m": 3475, "lda_m": 3475, "slope_pct": -0.40, "heading_deg": 262}
        }
    },
    "KGL": {
        "name": "Kigali Intl (Rwanda)",
        "elevation_ft": 4891,
        "runways": {
            "10": {"tora_m": 3500, "toda_m": 3500, "asda_m": 3500, "lda_m": 3500, "slope_pct": 0.20, "heading_deg": 98},
            "28": {"tora_m": 3500, "toda_m": 3500, "asda_m": 3500, "lda_m": 3500, "slope_pct": -0.20, "heading_deg": 278}
        }
    },
    "EBB": {
        "name": "Entebbe Intl (Uganda)",
        "elevation_ft": 3780,
        "runways": {
            "17": {"tora_m": 3658, "toda_m": 3658, "asda_m": 3658, "lda_m": 3658, "slope_pct": -0.15, "heading_deg": 172},
            "35": {"tora_m": 3658, "toda_m": 3658, "asda_m": 3658, "lda_m": 3658, "slope_pct": 0.15, "heading_deg": 352}
        }
    }
}

AIRCRAFT_AERO_SPECS = {
    "B737-800": {
        "name": "Boeing 737-800 CFM56-7B26",
        "mtow_structural_kg": 79010,
        "mlw_structural_kg": 66360,
        "base_tod_ref_m": 2100,
        "base_ld_ref_m": 1650,
        "flap_configs": {"Flaps 5": {"cl_factor": 1.0, "v1_bias": 0}, "Flaps 15": {"cl_factor": 1.08, "v1_bias": -4}, "Flaps 25": {"cl_factor": 1.15, "v1_bias": -8}},
        "climb_gradient_ref_pct": 4.2,
        "tire_speed_limit_kts": 195,
        "brake_energy_limit_mj": 82.0
    },
    "E190": {
        "name": "Embraer E190-E1 CF34-10E",
        "mtow_structural_kg": 51800,
        "mlw_structural_kg": 44000,
        "base_tod_ref_m": 1820,
        "base_ld_ref_m": 1380,
        "flap_configs": {"Flaps 1": {"cl_factor": 1.0, "v1_bias": 0}, "Flaps 2": {"cl_factor": 1.07, "v1_bias": -3}, "Flaps 4": {"cl_factor": 1.14, "v1_bias": -6}},
        "climb_gradient_ref_pct": 4.5,
        "tire_speed_limit_kts": 185,
        "brake_energy_limit_mj": 58.0
    }
}

# ---------------------------------------------------------
# 2. ATMOSPHERIC & AERODYNAMIC PERFORMANCE ENGINE
# ---------------------------------------------------------

def compute_isa_temperature(elevation_ft: float) -> float:
    """Standard ISA temperature at specified elevation (lapse rate 1.98°C/1000ft)."""
    return 15.0 - (1.98 * (elevation_ft / 1000.0))

def compute_pressure_altitude(elevation_ft: float, qnh_hpa: float) -> float:
    """Pressure altitude standard formula using standard 27 ft/hPa lapse rate."""
    return elevation_ft + (1013.25 - qnh_hpa) * 27.0

def compute_density_altitude(pressure_alt_ft: float, oat_c: float, elevation_ft: float) -> float:
    """Density altitude based on temperature deviation from standard ISA."""
    isa_temp = compute_isa_temperature(elevation_ft)
    isa_dev = oat_c - isa_temp
    return pressure_alt_ft + (120.0 * isa_dev)

def compute_runway_wind_components(wind_dir_deg: int, wind_spd_kts: float, rwy_heading_deg: int) -> dict:
    angle_rad = math.radians(wind_dir_deg - rwy_heading_deg)
    headwind = wind_spd_kts * math.cos(angle_rad)
    crosswind = abs(wind_spd_kts * math.sin(angle_rad))
    return {
        "headwind_kts": round(headwind, 1),
        "crosswind_kts": round(crosswind, 1)
    }

def evaluate_runway_field_performance(
    aircraft_type: str,
    airport_code: str,
    runway_id: str,
    oat_c: float,
    qnh_hpa: float,
    wind_dir: int,
    wind_spd: float,
    runway_condition: str,
    selected_flap: str,
    air_conditioning: str = "ON",
    anti_ice: str = "OFF"
) -> dict:
    ac = AIRCRAFT_AERO_SPECS[aircraft_type]
    apt = AIRPORTS_DATA[airport_code]
    rwy = apt["runways"][runway_id]
    
    elev = apt["elevation_ft"]
    p_alt = compute_pressure_altitude(elev, qnh_hpa)
    d_alt = compute_density_altitude(p_alt, oat_c, elev)
    isa_t = compute_isa_temperature(elev)
    isa_dev = oat_c - isa_t
    
    wind_comp = compute_runway_wind_components(wind_dir, wind_spd, rwy["heading_deg"])
    hw = wind_comp["headwind_kts"]
    
    density_penalty_factor = 1.0 + (max(0.0, d_alt) / 1000.0) * 0.035
    slope_penalty_factor = 1.0 + (rwy["slope_pct"] * 0.05)
    wind_credit = - (hw * 12.0)
    surface_penalty = 1.25 if runway_condition == "WET" else 1.0
    
    flap_cfg = ac["flap_configs"].get(selected_flap, list(ac["flap_configs"].values())[0])
    flap_cl = flap_cfg["cl_factor"]
    
    base_tod = (ac["base_tod_ref_m"] / flap_cl) * density_penalty_factor * slope_penalty_factor * surface_penalty + wind_credit
    
    bleed_pen_tod = 1.0
    if air_conditioning == "ON":
        bleed_pen_tod += 0.02
    if anti_ice == "ON":
        bleed_pen_tod += 0.05
    required_tod_m = max(1100.0, base_tod * bleed_pen_tod)
    
    avail_field = min(rwy["tora_m"], rwy["asda_m"])
    field_ratio = avail_field / required_tod_m
    field_limited_mtow_kg = ac["mtow_structural_kg"] * min(1.05, (field_ratio ** 0.65))
    
    climb_gradient_actual = ac["climb_gradient_ref_pct"] - (isa_dev * 0.05) - (p_alt / 1000.0 * 0.18)
    if anti_ice == "ON":
        climb_gradient_actual -= 0.35
    climb_limited_mtow_kg = ac["mtow_structural_kg"] * max(0.65, (climb_gradient_actual / 2.4))
    
    tire_limited_mtow_kg = ac["mtow_structural_kg"] * (1.0 - (d_alt / 25000.0))
    brake_energy_mtow_kg = ac["mtow_structural_kg"] * (1.05 if hw > 0 else 0.96)
    
    limits = {
        "Field Length Limit (TORA/ASDA)": round(field_limited_mtow_kg),
        "Climb Gradient Limit (2nd Segment OEI)": round(climb_limited_mtow_kg),
        "Tire Speed Limit": round(tire_limited_mtow_kg),
        "Brake Energy Limit": round(brake_energy_mtow_kg),
        "Certified Structural Limit": ac["mtow_structural_kg"]
    }
    
    limiting_code = min(limits, key=limits.get)
    regulated_mtow_kg = min(limits.values())
    
    weight_factor = (regulated_mtow_kg / ac["mtow_structural_kg"]) ** 0.5
    v1 = int((138 + (flap_cfg.get("v1_bias", 0)) + (hw * 0.2) + (p_alt / 2000.0)) * weight_factor)
    vr = int(v1 + 4)
    v2 = int(vr + 8)
    
    base_ld = ac["base_ld_ref_m"] * (1.0 + (d_alt / 1000.0 * 0.02)) - (hw * 10.0)
    factored_ld_m = base_ld * (1.92 if runway_condition == "WET" else 1.67)
    
    landing_field_ratio = rwy["lda_m"] / factored_ld_m
    field_limited_mldw_kg = ac["mlw_structural_kg"] * min(1.04, (landing_field_ratio ** 0.70))
    regulated_mldw_kg = min(ac["mlw_structural_kg"], field_limited_mldw_kg)
    vref = int((132 + (regulated_mldw_kg / ac["mlw_structural_kg"] * 10)))
    
    return {
        "aircraft_name": ac["name"],
        "airport_name": apt["name"],
        "runway_id": runway_id,
        "runway_condition": runway_condition,
        "atmospherics": {
            "pressure_alt_ft": round(p_alt),
            "density_alt_ft": round(d_alt),
            "isa_temp_c": round(isa_t, 1),
            "isa_dev_c": round(isa_dev, 1),
            "headwind_kts": wind_comp["headwind_kts"],
            "crosswind_kts": wind_comp["crosswind_kts"]
        },
        "limits": limits,
        "limiting_condition": limiting_code,
        "regulated_mtow_kg": round(regulated_mtow_kg),
        "required_tod_m": round(required_tod_m),
        "available_tod_m": avail_field,
        "v_speeds": {"v1_kts": v1, "vr_kts": vr, "v2_kts": v2},
        "landing": {
            "regulated_mldw_kg": round(regulated_mldw_kg),
            "required_lda_factored_m": round(factored_ld_m),
            "available_lda_m": rwy["lda_m"],
            "vref_kts": vref,
            "is_landing_legal": factored_ld_m <= rwy["lda_m"]
        }
    }

# ---------------------------------------------------------
# 3. STREAMLIT USER INTERFACE
# ---------------------------------------------------------

st.title("🛫 Runway Performance & Field Limits Calculator")
st.caption("Flight Operations Engineering Dispatch Platform | Takeoff & Landing Performance (RTOW / RLDW)")

st.sidebar.header("✈️ Fleet & Aerodrome Configuration")

ac_selected = st.sidebar.selectbox("Fleet Aircraft Type", list(AIRCRAFT_AERO_SPECS.keys()), index=0)
ac_spec = AIRCRAFT_AERO_SPECS[ac_selected]

apt_selected = st.sidebar.selectbox("Departure / Arrival Aerodrome", list(AIRPORTS_DATA.keys()), index=0)
apt_data = AIRPORTS_DATA[apt_selected]

rwy_options = list(apt_data["runways"].keys())
rwy_selected = st.sidebar.selectbox("Active Runway", rwy_options, index=0)
rwy_data = apt_data["runways"][rwy_selected]

st.sidebar.subheader("🌡️ Atmospheric & Weather Conditions")
oat = st.sidebar.slider("Outside Air Temperature (OAT °C)", -10, 48, 24, step=1)
qnh = st.sidebar.slider("Station QNH (hPa)", 980, 1040, 1018, step=1)
wind_dir = st.sidebar.slider("Surface Wind Direction (°T)", 0, 360, int(rwy_data["heading_deg"]), step=10)
wind_spd = st.sidebar.slider("Surface Wind Speed (kts)", 0, 50, 12, step=1)

st.sidebar.subheader("⚙️ Aircraft Takeoff Configuration")
rwy_cond = st.sidebar.selectbox("Runway Surface Condition", ["DRY", "WET"], index=0)
flap_opt = list(ac_spec["flap_configs"].keys())
selected_flap = st.sidebar.selectbox("Takeoff Flap Setting", flap_opt, index=0)

c_bleed1, c_bleed2 = st.sidebar.columns(2)
with c_bleed1:
    ac_bleed = st.selectbox("Packs / Air Cond", ["ON", "OFF"], index=0)
with c_bleed2:
    anti_ice = st.selectbox("Engine Anti-Ice", ["OFF", "ON"], index=0)

perf = evaluate_runway_field_performance(
    aircraft_type=ac_selected,
    airport_code=apt_selected,
    runway_id=rwy_selected,
    oat_c=oat,
    qnh_hpa=qnh,
    wind_dir=wind_dir,
    wind_spd=wind_spd,
    runway_condition=rwy_cond,
    selected_flap=selected_flap,
    air_conditioning=ac_bleed,
    anti_ice=anti_ice
)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric(
        "Regulated MTOW (PLMTOW)",
        f"{perf['regulated_mtow_kg']:,} kg",
        delta=f"Structural: {ac_spec['mtow_structural_kg']:,} kg"
    )
with k2:
    st.metric(
        "Limiting Factor",
        perf["limiting_condition"]
    )
with k3:
    st.metric(
        "Takeoff V-Speeds",
        f"V1: {perf['v_speeds']['v1_kts']} | VR: {perf['v_speeds']['vr_kts']} | V2: {perf['v_speeds']['v2_kts']}",
        delta=f"VREF: {perf['landing']['vref_kts']} kts"
    )
with k4:
    hw = perf["atmospherics"]["headwind_kts"]
    st.metric(
        "Headwind / Crosswind",
        f"{'+' if hw>=0 else ''}{hw} kts / {perf['atmospherics']['crosswind_kts']} kts",
        delta=f"Density Alt: {perf['atmospherics']['density_alt_ft']:,} ft"
    )

st.divider()

t1, t2, t3, t4 = st.tabs(["📊 Performance Limiting Analysis", "🛫 Takeoff Runway Distance & V-Speeds", "🛬 Factored Landing Assessment", "🌤️ Atmospherics & Density Altitude"])

with t1:
    st.subheader(f"Takeoff Performance Limits Comparison: Runway {rwy_selected} ({apt_data['name']})")
    
    df_limits = pd.DataFrame({
        "Performance Boundary Condition": list(perf["limits"].keys()),
        "Allowable Takeoff Weight (kg)": list(perf["limits"].values()),
        "Status": ["ACTIVE GOVERNING LIMIT" if k == perf["limiting_condition"] else "Satisfied" for k in perf["limits"].keys()]
    })
    
    c_lim1, c_lim2 = st.columns(2)
    with c_lim1:
        st.dataframe(df_limits.style.format({"Allowable Takeoff Weight (kg)": "{:,.0f}"}), use_container_width=True)
    
    with c_lim2:
        fig_bar = go.Figure(go.Bar(
            x=list(perf["limits"].values()),
            y=list(perf["limits"].keys()),
            orientation='h',
            marker_color=["#DC2626" if k == perf["limiting_condition"] else "#1E3A8A" for k in perf["limits"].keys()]
        ))
        fig_bar.update_layout(
            title="Weight Restrictions Across Regulatory Boundaries (kg)",
            xaxis_title="Max Allowable Weight (kg)",
            height=320,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with t2:
    st.subheader(f"Takeoff Field Runway Margins (TORA: {perf['available_tod_m']} m)")
    
    fig_rwy = go.Figure()
    
    fig_rwy.add_trace(go.Bar(
        name="Available TORA / ASDA",
        x=["Runway Field Length"],
        y=[perf["available_tod_m"]],
        marker_color="#94A3B8"
    ))
    
    fig_rwy.add_trace(go.Bar(
        name="Required Takeoff Distance (TOD)",
        x=["Runway Field Length"],
        y=[perf["required_tod_m"]],
        marker_color="#1E3A8A"
    ))
    
    fig_rwy.update_layout(
        barmode='group',
        title=f"Required TOD ({perf['required_tod_m']} m) vs Available Runway ({perf['available_tod_m']} m)",
        yaxis_title="Meters (m)",
        height=320,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig_rwy, use_container_width=True)
    
    st.markdown(f"""
    ```text
    ================================================================================
    TAKEOFF V-SPEEDS & PERFORMANCE DISPATCH SUMMARY
    AIRCRAFT: {ac_spec['name']}          RUNWAY: {apt_selected} RWY {rwy_selected}
    REGULATED MTOW: {perf['regulated_mtow_kg']:,} KG                   LIMITING: {perf['limiting_condition'].upper()}
    --------------------------------------------------------------------------------
    DECISION SPEED (V1):     {perf['v_speeds']['v1_kts']:>3} KTS
    ROTATION SPEED (VR):     {perf['v_speeds']['vr_kts']:>3} KTS
    TAKEOFF SAFETY (V2):     {perf['v_speeds']['v2_kts']:>3} KTS
    REQUIRED FIELD LENGTH:   {perf['required_tod_m']:>4} M       (STOPWAY/CLEARWAY MARGIN: {perf['available_tod_m'] - perf['required_tod_m']:>4} M)
    ================================================================================
    ```
    """)

with t3:
    st.subheader(f"Regulated Landing Performance (Factored Dispatch Distance)")
    land = perf["landing"]
    
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l1:
        st.metric("Regulated MLDW", f"{land['regulated_mldw_kg']:,} kg", delta=f"Structural: {ac_spec['mlw_structural_kg']:,} kg")
    with col_l2:
        st.metric("Factored Required LDA", f"{land['required_lda_factored_m']:,} m", delta="60% Rule (Dry) / 115% (Wet)")
    with col_l3:
        st.metric("Available Landing Dist (LDA)", f"{land['available_lda_m']:,} m", delta="DISPATCH LEGAL" if land["is_landing_legal"] else "RESTRICTED")
        
    if land["is_landing_legal"]:
        st.success(f"""
        **DISPATCH LANDING PERFORMANCE SATISFIED**
        * Factored Landing Distance (`{land['required_lda_factored_m']} m`) is within physical LDA (`{land['available_lda_m']} m`).
        * Margin remaining: `{land['available_lda_m'] - land['required_lda_factored_m']} meters`.
        * Approach target threshold speed: **VREF {land['vref_kts']} kts**.
        """)
    else:
        st.error(f"""
        **LANDING RUNWAY RESTRICTION EXCEEDED**
        * Factored required landing distance exceeds available LDA by `{land['required_lda_factored_m'] - land['available_lda_m']} meters`.
        """)

with t4:
    st.subheader("Atmospheric Telemetry & Standard ISA Offsets")
    atm = perf["atmospherics"]
    
    c_a1, c_a2 = st.columns(2)
    with c_a1:
        st.write(f"**Aerodrome Elevation:** `{apt_data['elevation_ft']} ft MSL`")
        st.write(f"**Station QNH:** `{qnh} hPa`")
        st.write(f"**Pressure Altitude ($H_p$):** `{atm['pressure_alt_ft']} ft`")
        st.write(f"**Density Altitude ($H_d$):** `{atm['density_alt_ft']} ft`")
    with c_a2:
        st.write(f"**Standard ISA Temperature at {apt_data['elevation_ft']} ft:** `{atm['isa_temp_c']} °C`")
        st.write(f"**Actual Outside Air Temperature (OAT):** `{oat} °C`")
        st.write(f"**ISA Deviation ($\\Delta \\text{{ISA}}$):** `{'+' if atm['isa_dev_c']>0 else ''}{atm['isa_dev_c']} °C`")
        st.write(f"**Headwind Component:** `{atm['headwind_kts']} kts` | **Crosswind:** `{atm['crosswind_kts']} kts`")

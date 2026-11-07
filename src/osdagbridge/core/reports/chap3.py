# =============================================================================
# Chapter 3: Loads and Load Combinations
# Separate tables for vehicular live load and footway live load.
# Repeated headers and continuation footers for all multipage tables.
# =============================================================================

import logging
import math

logger = logging.getLogger(__name__)

from osdagbridge.core.utils.common import (
    KEY_BL_IRC_CLASS_SV,
    KEY_CARRIAGEWAY_WIDTH,
    KEY_CB_LOAD,
    KEY_FOOTPATH,
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_MATERIAL_GIRDER_DENSITY,
    KEY_PL_SELF_WEIGHT_FACTOR,
    KEY_RL_LOAD_VALUE,
    KEY_SL_DAMPING,
    KEY_SL_DEAD_LOAD_MODE,
    KEY_SL_DEAD_LOAD_VALUE,
    KEY_SL_HORIZONTAL_COEFF,
    KEY_SL_IMPORTANCE_FACTOR,
    KEY_SL_LIVE_LOAD_MODE,
    KEY_SL_LIVE_LOAD_VALUE,
    KEY_SL_SEISMIC_ZONE,
    KEY_SL_SOIL_TYPE,
    KEY_SL_SPECTRAL_COEFF,
    KEY_SL_TIME_PERIOD,
    KEY_SL_VERTICAL_COEFF,
    KEY_SL_ZONE_FACTOR,
    KEY_SPAN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_TS_FOOTPATH_WIDTH,
    KEY_TS_NO_OF_FOOTPATHS,
    KEY_WC_LD_LANE_TABLE,
    KEY_WC_LD_LANE_TABLE_COUNT,
    KEY_WC_MATERIAL,
    KEY_WC_THICKNESS,
    KEY_WL_AVG_EXPOSED_HEIGHT,
    KEY_WL_BASIC_WIND_SPEED,
    KEY_WL_HOURLY_MEAN_WIND,
    KEY_WL_HOURLY_WIND_PRESSURE,
    KEY_WL_LONGITUDINAL_WIND_FORCE,
    KEY_WL_TERRAIN_TYPE,
    KEY_WL_TRANSVERSE_WIND_FORCE,
    KEY_WL_VERTICAL_WIND_FORCE,
)

from osdagbridge.core.reports.report_utils import _tex, _render_value
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017


def ch3_loads(input_dict):
    # ── 1. Live Load Vehicles Matching UI ──────────────────────────────────────
    vehicles = []
    vehicle_rows = []

    vehicle_defs = [
        (KEY_LL_IRC_CLASS_A, "Class A", "Wheeled train (Clause 204.1)"),
        (KEY_LL_IRC_AA_WHEELED, "Class AA (Wheeled)", "Wheeled vehicle 400 kN (Clause 204.1)"),
        (KEY_LL_IRC_AA_TRACKED, "Class AA (Tracked)", "Tracked vehicle 700 kN (Clause 204.1)"),
        (KEY_LL_IRC_70R_WHEELED, "Class 70R (Wheeled)", "Wheeled vehicle 1000 kN (Clause 204.1)"),
        (KEY_LL_IRC_70R_TRACKED, "Class 70R (Tracked)", "Tracked vehicle 700 kN (Clause 204.1)"),
        (KEY_LL_IRC_70R_BOGIE, "Class 70R (Bogie)", "Bogie vehicle 400 kN (Clause 204.1)"),
        (KEY_LL_IRC_CLASS_SV, "Class SV", "Special Vehicle per Ministry circular (IRC 6)"),
        (KEY_LL_IRC_CLASS_FATIGUE, "Class Fatigue", "Fatigue vehicle (Clause 204.6)"),
    ]

    for key, name, desc in vehicle_defs:
        is_sel = bool(input_dict.get(key))
        if is_sel:
            vehicles.append(name)
            vehicle_rows.append(
                f"\\textnormal{{{name}}} & {desc} & \\textcolor{{passGreen}}{{\\textbf{{Considered}}}} \\\\[4pt]\n\\hline"
            )

    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if custom and isinstance(custom, list):
        for c in custom:
            c_name = c.get("name", "Custom Vehicle") if isinstance(c, dict) else str(c)
            vehicles.append(c_name)
            vehicle_rows.append(
                f"\\textnormal{{{_tex(c_name)}}} & User-defined custom vehicle & \\textcolor{{passGreen}}{{\\textbf{{Considered}}}} \\\\[4pt]\n\\hline"
            )

    if not vehicle_rows:
        vehicle_rows.append(
            r"\textnormal{None} & No vehicular live load selected & \textcolor{failRed}{\textbf{Excluded}} \\[4pt]" + "\n\\hline"
        )

    vehicles_table_body = "\n".join(vehicle_rows)

    # ── 2. Impact Factor (IRC 6 Clause 208) ────────────────────────────────────
    span = input_dict.get(KEY_SPAN)
    impact_factor_str = "N/A"
    if span not in (None, ""):
        try:
            span_m = float(span)
            factors = []
            if input_dict.get(KEY_LL_IRC_CLASS_A):
                im_a = IRC6_2017.cl_208_2_impact_factor(span_m)
                factors.append(f"Class A: {1.0 + im_a:.3f} (IRC 6 Cl. 208.2)")
            is_wheeled_heavy = (
                input_dict.get(KEY_LL_IRC_70R_WHEELED)
                or input_dict.get(KEY_LL_IRC_AA_WHEELED)
                or input_dict.get(KEY_LL_IRC_70R_BOGIE)
            )
            is_tracked_heavy = (
                input_dict.get(KEY_LL_IRC_70R_TRACKED)
                or input_dict.get(KEY_LL_IRC_AA_TRACKED)
            )
            if is_wheeled_heavy or is_tracked_heavy:
                im_aa = IRC6_2017.cl_208_3_impact_factor(span_m)
                factors.append(f"Class AA / 70R: {1.0 + im_aa:.3f} (IRC 6 Cl. 208.3)")

            if factors:
                impact_factor_str = ", ".join(factors)
        except Exception as exc:
            logger.warning("Impact factor calculation failed: %s", exc)
            impact_factor_str = r"\textcolor{failRed}{Calculation Error (Inspect engine log)}"

    # ── 3. Braking Force (IRC 6 Clause 211) ────────────────────────────────────
    lanes = input_dict.get(KEY_WC_LD_LANE_TABLE_COUNT)
    if lanes in (None, ""):
        # Fallback 1: check length of lane table rows
        lane_table = input_dict.get(KEY_WC_LD_LANE_TABLE)
        if isinstance(lane_table, list) and len(lane_table) > 0:
            lanes = len(lane_table)
        else:
            # Fallback 2: derive from carriageway width per IRC 5 Cl. 104.3.1
            cw = (
                input_dict.get(KEY_CARRIAGEWAY_WIDTH)
                or input_dict.get("typical_section.carriageway_width")
                or input_dict.get("carriageway_width")
            )
            try:
                if cw is not None and float(cw) > 0:
                    cw_f = float(cw)
                    if cw_f < 5.3:
                        lanes = 1
                    elif cw_f < 9.6:
                        lanes = 2
                    elif cw_f < 13.1:
                        lanes = 3
                    else:
                        lanes = max(1, min(6, int(math.floor(cw_f / 3.5))))
            except Exception:
                pass

    braking_force_str = "Not Specified"
    if lanes not in (None, ""):
        try:
            lanes_int = int(lanes)
            braking_force_t = IRC6_2017.cl_211_2_braking_force(lanes_int)
            braking_force_kN = braking_force_t * 9.81
            braking_force_str = (
                f"{braking_force_kN:.2f} kN ({braking_force_t:.2f} tonnes for {lanes_int} lane{'s' if lanes_int > 1 else ''})"
            )
        except Exception as exc:
            logger.error("Braking force calculation failed for lanes=%s: %s", lanes, exc, exc_info=True)
            braking_force_str = r"\textcolor{failRed}{Calculation Error (Inspect engine log)}"

    # Eccentricity
    ecc_val = input_dict.get(KEY_LL_ECCENTRICITY)
    if ecc_val not in (None, ""):
        ecc_str = f"{ecc_val} m above deck surface"
    else:
        ecc_str = "1.20 m above deck surface (IRC 6 Cl. 211.3 default)"

    # Class SV braking opt-in
    sv_braking_val = input_dict.get(KEY_BL_IRC_CLASS_SV)
    if sv_braking_val in (True, "True", "true", 1, "1"):
        sv_braking_str = "Included (user opted-in)"
    else:
        sv_braking_str = "Excluded (not mandatory per IRC 6 Cl. 211)"

    # ── 4. Footway Load (IRC 6 Clause 206) ─────────────────────────────────────
    fp_mode = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "")
    fp_value = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE, "")
    if str(fp_mode).strip().lower() in ("as per irc 6", "as per irc6", "automatic"):
        try:
            fp_intensity_str = f"{IRC6_2017.cl_206_1_footway_load():.3f} kN/m² (per IRC 6 Cl. 206.1)"
        except Exception as exc:
            logger.warning("Footway load calculation failed: %s", exc)
            fp_intensity_str = r"\textcolor{failRed}{Calculation Error (Inspect engine log)}"
    elif fp_value not in (None, ""):
        fp_intensity_str = f"{fp_value} kN/m² (Custom input)"
    else:
        fp_intensity_str = "N/A"

    fp_config = input_dict.get(KEY_FOOTPATH) or input_dict.get(KEY_TS_NO_OF_FOOTPATHS) or "None"
    fp_width = input_dict.get(KEY_TS_FOOTPATH_WIDTH)
    fp_width_str = f"{fp_width} m" if fp_width not in (None, "") else "---"

    # ── 5. Wind Load (WL) ──────────────────────────────────────────────────────
    vz_val = input_dict.get(KEY_WL_HOURLY_MEAN_WIND)
    pz_val = input_dict.get(KEY_WL_HOURLY_WIND_PRESSURE)
    if not vz_val or not pz_val:
        try:
            _vb = input_dict.get(KEY_WL_BASIC_WIND_SPEED) or input_dict.get("wind_speed")
            _h = input_dict.get(KEY_WL_AVG_EXPOSED_HEIGHT)
            _ter = {
                "Plain Terrain": "plain",
                "Terrain with Obstructions": "obstructed",
            }.get(str(input_dict.get(KEY_WL_TERRAIN_TYPE, "")).strip(), "plain")
            if _h and _vb:
                _res = IRC6_2017.table_12(float(_h), _ter, float(_vb))
                if not vz_val:
                    vz_val = _res.get("Vz")
                if not pz_val:
                    pz_val = _res.get("Pz")
        except Exception:
            pass
    vz_str = f"{float(vz_val):.2f} m/s" if vz_val not in (None, "") else "N/A"
    pz_str = f"{float(pz_val):.2f} N/m²" if pz_val not in (None, "") else "N/A"

    # ── 6. Seismic Load (EL) ───────────────────────────────────────────────────
    sl_zone_factor = input_dict.get(KEY_SL_ZONE_FACTOR)
    sl_spectral = input_dict.get(KEY_SL_SPECTRAL_COEFF)
    sl_ah = input_dict.get(KEY_SL_HORIZONTAL_COEFF)
    sl_av = input_dict.get(KEY_SL_VERTICAL_COEFF)
    if not sl_ah or not sl_zone_factor:
        try:
            _zone = input_dict.get(KEY_SL_SEISMIC_ZONE) or input_dict.get("seismic_zone")
            _zmap = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V"}
            _z = str(_zone).strip().upper()
            if _z.isdigit():
                _z = _zmap.get(_z)
            _smap = {"Type I – Rocky or Hard": 1, "Type II – Medium Soil": 2, "Type III – Soft Soil": 3}
            _st = _smap.get(str(input_dict.get(KEY_SL_SOIL_TYPE, "")), 1)
            _tp = input_dict.get(KEY_SL_TIME_PERIOD)
            _damp = input_dict.get(KEY_SL_DAMPING) or "5"
            _dl_v = input_dict.get(KEY_SL_DEAD_LOAD_VALUE)
            _ll_v = input_dict.get(KEY_SL_LIVE_LOAD_VALUE)
            _dead = float(_dl_v) if str(input_dict.get(KEY_SL_DEAD_LOAD_MODE, "")) == "Custom" and _dl_v else 0.0
            _live = float(_ll_v) if str(input_dict.get(KEY_SL_LIVE_LOAD_MODE, "")) == "Custom" and _ll_v else 0.0
            _res = IRC6_2017.cl_218_5_1(
                zone=f"Zone {_z}",
                soil_type=_st,
                dead_load_kN=_dead,
                live_load_kN=_live,
                period_T=float(_tp) if _tp else None,
                damping_percent=float(_damp),
            )
            if not sl_zone_factor:
                sl_zone_factor = _res.get("Z")
            if not sl_spectral:
                sl_spectral = _res.get("Sa_g_adjusted")
            if not sl_ah:
                sl_ah = _res.get("Ah")
            if not sl_av:
                sl_av = round(_res.get("Ah", 0) * 2 / 3, 4)
        except Exception:
            pass

    # ── 7. Temperature Load (TL) ───────────────────────────────────────────────
    tl_temp_min = tl_temp_max = tl_rise = tl_fall = "N/A"
    try:
        _tmax = input_dict.get(KEY_TL_HIGHEST_MAX_TEMP) or input_dict.get("shade_temp_max")
        _tmin = input_dict.get(KEY_TL_LOWEST_MIN_TEMP) or input_dict.get("shade_temp_min")
        if _tmax and _tmin:
            _res = IRC6_2017.cl_215_2_effective_bridge_temperature(
                float(_tmax), float(_tmin), "metallic", False
            )
            _bt_min = _res.get("T_min", 0)
            _bt_max = _res.get("T_max", 0)
            _mean = (_bt_max + _bt_min) / 2.0
            tl_temp_min = f"{_bt_min:.2f}"
            tl_temp_max = f"{_bt_max:.2f}"
            tl_rise = f"{_bt_max - _mean:.2f}"
            tl_fall = f"{_mean - _bt_min:.2f}"
    except Exception:
        pass

    # ── 8. Load Combinations (IRC 6) ──────────────────────────────────────────
    _LOAD_LABEL_MAP = {
        "dead_load": "DL",
        "surfacing": "SIDL",
        "live_load": "LL",
        "wind_load": "WL",
        "thermal_load": "TL",
        "vehicle_collision": "VC",
        "barge_impact": "BI",
        "floating_bodies": "FB",
        "seismic": "EQ",
    }

    def _fmt_factors(factors):
        parts = []
        for load, val in factors.items():
            label = _LOAD_LABEL_MAP.get(load, load.upper())
            if isinstance(val, dict):
                add = val.get("adding")
                rel = val.get("relieving")
                add_s = f"{add:.2f}" if add is not None else "--"
                rel_s = f"{rel:.2f}" if rel is not None else "--"
                parts.append(f"{label}({add_s}/{rel_s})")
            else:
                if val is None:
                    continue
                parts.append(f"{label}({val:.2f})")
        return " + ".join(parts)

    uls_combos = IRC6_2017.uls_load_combinations()
    sls_combos = IRC6_2017.sls_load_combinations()
    lc_rows = []
    for i, combo in enumerate(uls_combos, start=1):
        cases = _fmt_factors(combo["factors"])
        lc_rows.append(
            f"ULS-{i:02d}" + r" & " + cases + r" \\[6pt]" + "\n" + r"\hline"
        )
    for i, combo in enumerate(sls_combos, start=1):
        cases = _fmt_factors(combo["factors"])
        lc_rows.append(
            f"SLS-{i:02d}" + r" & " + cases + r" \\[6pt]" + "\n" + r"\hline"
        )

    lc_rows_str = "\n".join(lc_rows)

    return r"""
\chapter{Loads and Load Combinations}
\label{ch:loads}

This chapter details all primary and secondary actions considered in the analysis and design of the bridge superstructure, per IRC~6:2017. Vehicular live loads and pedestrian footway actions are evaluated independently in accordance with the codified provisions.

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Dead Load --- Self Weight}} \label{tab:dl-self-weight} \\
\hline
\textbf{Parameter} & \textbf{Design Value / Specification} \\[6pt]
\hline
\endfirsthead
\multicolumn{2}{c}{{\small\textit{(Table Dead Load --- Self Weight --- Continued from previous page)}}} \\[4pt]
\hline
\textbf{Parameter} & \textbf{Design Value / Specification} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{{\scriptsize\textit{Continued on next page\dots}}} \\
\endfoot
\hline
\endlastfoot
\textnormal{Steel Density Applied} & """ + (_render_value(input_dict, KEY_MATERIAL_GIRDER_DENSITY, r' $\text{kN/m}^3$')) + r""" \\[6pt]
\hline
\textnormal{Concrete Deck Density} & """ + (_render_value(input_dict, KEY_MATERIAL_DECK_DENSITY, r' $\text{kN/m}^3$')) + r""" \\[6pt]
\hline
\textnormal{Self-Weight Factor} & """ + (_render_value(input_dict, KEY_PL_SELF_WEIGHT_FACTOR)) + r""" \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Superimposed Dead Load (SIDL) --- Surfacing \& Fixtures}} \label{tab:sidl} \\
\hline
\textbf{Parameter} & \textbf{Design Value / Specification} \\[6pt]
\hline
\endfirsthead
\multicolumn{2}{c}{{\small\textit{(Table SIDL --- Continued from previous page)}}} \\[4pt]
\hline
\textbf{Parameter} & \textbf{Design Value / Specification} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{{\scriptsize\textit{Continued on next page\dots}}} \\
\endfoot
\hline
\endlastfoot
\textnormal{Wearing Course Material \& Thickness} & """ + (_render_value(input_dict, KEY_WC_MATERIAL)) + r""" $\times$ """ + (_render_value(input_dict, KEY_WC_THICKNESS, ' mm')) + r""" \\[6pt]
\hline
\textnormal{Crash Barrier SIDL} & """ + (_render_value(input_dict, KEY_CB_LOAD)) + r""" kN/m per barrier \\[6pt]
\hline
\textnormal{Railing Load} & """ + (_render_value(input_dict, KEY_RL_LOAD_VALUE)) + r""" kN/m\sdstar{} \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{4.5cm}|L{7.5cm}|C{3.2cm}|}
\caption{\textbf{Vehicular Live Load Selection (IRC 6 Clause 204)}} \label{tab:vehicular-live-load} \\
\hline
\textbf{Vehicle Class} & \textbf{Standard Definition / Axle Configuration} & \textbf{Status in Model} \\[6pt]
\hline
\endfirsthead
\multicolumn{3}{c}{{\small\textit{(Table Vehicular Live Load Selection --- Continued from previous page)}}} \\[4pt]
\hline
\textbf{Vehicle Class} & \textbf{Standard Definition / Axle Configuration} & \textbf{Status in Model} \\[6pt]
\hline
\endhead
\hline
\multicolumn{3}{r}{{\scriptsize\textit{Continued on next page\dots}}} \\
\endfoot
\hline
\endlastfoot
""" + vehicles_table_body + r"""
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Vehicular Dynamic, Braking, and Centrifugal Effects}} \label{tab:vehicular-effects} \\
\hline
\textbf{Action / Effect} & \textbf{Design Parameter / Codified Basis} \\[6pt]
\hline
\endfirsthead
\multicolumn{2}{c}{{\small\textit{(Table Vehicular Dynamic \& Braking Effects --- Continued from previous page)}}} \\[4pt]
\hline
\textbf{Action / Effect} & \textbf{Design Parameter / Codified Basis} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{{\scriptsize\textit{Continued on next page\dots}}} \\
\endfoot
\hline
\endlastfoot
\textnormal{Dynamic Impact Factor ($1 + I$)} & """ + (_tex(impact_factor_str) if r"\textcolor" not in impact_factor_str else impact_factor_str) + r""" \\[6pt]
\hline
\textnormal{Longitudinal Braking Force} & """ + (_tex(braking_force_str) if r"\textcolor" not in braking_force_str else braking_force_str) + r""" (IRC 6 Cl. 211.2) \\[6pt]
\hline
\textnormal{Braking Force Application Height} & """ + _tex(ecc_str) + r""" \\[6pt]
\hline
\textnormal{Class SV Braking Force Consideration} & """ + _tex(sv_braking_str) + r""" \\[6pt]
\hline
\textnormal{Centrifugal Force (IRC 6 Cl. 212)} & \textit{Not Applicable} (No horizontal curvature modelled; bridge geometry has straight alignment per IRC 6 Cl. 212) \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Footway / Pedestrian Live Load (IRC 6 Clause 206)}} \label{tab:footway-load} \\
\hline
\textbf{Parameter} & \textbf{Design Value / Codified Basis} \\[6pt]
\hline
\endfirsthead
\multicolumn{2}{c}{{\small\textit{(Table Footway Live Load --- Continued from previous page)}}} \\[4pt]
\hline
\textbf{Parameter} & \textbf{Design Value / Codified Basis} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{{\scriptsize\textit{Continued on next page\dots}}} \\
\endfoot
\hline
\endlastfoot
\textnormal{Footpath Configuration} & """ + _tex(str(fp_config)) + r""" \\[6pt]
\hline
\textnormal{Footpath Width} & """ + _tex(fp_width_str) + r""" \\[6pt]
\hline
\textnormal{Footway Loading Intensity} & """ + (_tex(fp_intensity_str) if r"\textcolor" not in fp_intensity_str else fp_intensity_str) + r""" \\[6pt]
\hline
\textnormal{Simultaneous Live Load Reduction} & Considered in combined load cases per IRC 6 Cl. 206.1 \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Wind Load (WL) --- per IRC 6 Table 12}} \label{tab:wind-load} \\
\hline
\textbf{Parameter} & \textbf{Design Value} \\[6pt]
\hline
\endfirsthead
\multicolumn{2}{c}{{\small\textit{(Table Wind Load --- Continued from previous page)}}} \\[4pt]
\hline
\textbf{Parameter} & \textbf{Design Value} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{{\scriptsize\textit{Continued on next page\dots}}} \\
\endfoot
\hline
\endlastfoot
\textnormal{Basic Wind Speed, $V_b$} & """ + (_render_value(input_dict, 'wind_speed', ' m/s')) + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Terrain Type} & """ + (_render_value(input_dict, KEY_WL_TERRAIN_TYPE)) + r""" \\[6pt]
\hline
\textnormal{Average Exposed Height, $H$} & """ + (_render_value(input_dict, KEY_WL_AVG_EXPOSED_HEIGHT, ' m')) + r""" \\[6pt]
\hline
\textnormal{Hourly Mean Wind Speed, $V_z$} & """ + _tex(vz_str) + r""" \\[6pt]
\hline
\textnormal{Hourly Wind Pressure, $P_z$} & """ + _tex(pz_str) + r""" \\[6pt]
\hline
\textnormal{Transverse Wind Force} & """ + (_render_value(input_dict, KEY_WL_TRANSVERSE_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\textnormal{Longitudinal Wind Force} & """ + (_render_value(input_dict, KEY_WL_LONGITUDINAL_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\textnormal{Vertical Wind Force} & """ + (_render_value(input_dict, KEY_WL_VERTICAL_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Earthquake Load (EL) --- per IRC 6 Clause 218}} \label{tab:seismic-load} \\
\hline
\textbf{Parameter} & \textbf{Design Value} \\[6pt]
\hline
\endfirsthead
\multicolumn{2}{c}{{\small\textit{(Table Earthquake Load --- Continued from previous page)}}} \\[4pt]
\hline
\textbf{Parameter} & \textbf{Design Value} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{{\scriptsize\textit{Continued on next page\dots}}} \\
\endfoot
\hline
\endlastfoot
\textnormal{Seismic Zone} & """ + (_render_value(input_dict, 'seismic_zone')) + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Zone Factor, $Z$} & """ + (_render_value(input_dict, KEY_SL_ZONE_FACTOR)) + r""" \\[6pt]
\hline
\textnormal{Importance Factor, $I$} & """ + (_render_value(input_dict, KEY_SL_IMPORTANCE_FACTOR)) + r""" \\[6pt]
\hline
\textnormal{Type of Soil} & """ + (_render_value(input_dict, KEY_SL_SOIL_TYPE)) + r""" \\[6pt]
\hline
\textnormal{Spectral Acceleration, $S_a/g$} & """ + (_render_value(input_dict, KEY_SL_SPECTRAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Coeff., $A_h$} & """ + (_render_value(input_dict, KEY_SL_HORIZONTAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Vertical Seismic Coeff., $A_v$} & """ + (_render_value(input_dict, KEY_SL_VERTICAL_COEFF)) + r""" \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Temperature Load (TL) --- per IRC 6 Clause 215}} \label{tab:temperature-load} \\
\hline
\textbf{Parameter} & \textbf{Design Value} \\[6pt]
\hline
\endfirsthead
\multicolumn{2}{c}{{\small\textit{(Table Temperature Load --- Continued from previous page)}}} \\[4pt]
\hline
\textbf{Parameter} & \textbf{Design Value} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{{\scriptsize\textit{Continued on next page\dots}}} \\
\endfoot
\hline
\endlastfoot
\textnormal{Maximum Shade Temperature} & """ + (_render_value(input_dict, 'shade_temp_max')) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Minimum Shade Temperature} & """ + (_render_value(input_dict, 'shade_temp_min')) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Effective Bridge Temp. Range} & """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MIN)) + r""" to """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MAX)) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Temperature Rise / Fall for Design} & +""" + (_render_value(input_dict, KEY_TL_TEMP_RISE)) + r""" $^\circ$C / \textminus{}""" + (_render_value(input_dict, KEY_TL_TEMP_FALL)) + r""" $^\circ$C \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|C{3.5cm}|p{12.0cm}|}
\caption{\textbf{Load Combinations (per IRC 6 Table B.1 -- B.4)}} \label{tab:load-combinations} \\
\hline
\textbf{Combination ID} & \textbf{Factored Load Components} \\[6pt]
\hline
\endfirsthead
\multicolumn{2}{c}{{\small\textit{(Table Load Combinations --- Continued from previous page)}}} \\[4pt]
\hline
\textbf{Combination ID} & \textbf{Factored Load Components} \\[6pt]
\hline
\endhead
\hline
\multicolumn{2}{r}{{\scriptsize\textit{Continued on next page\dots}}} \\
\endfoot
\hline
\endlastfoot
""" + lc_rows_str + r"""
\end{longtable}

\noindent\textit{Note: All IRC 6 load combinations are auto-generated by OsdagBridge per Table B.1 (ULS) and Table B.2 (SLS). User-defined custom combinations, if specified, are appended.}
"""

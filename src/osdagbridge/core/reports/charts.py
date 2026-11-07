# =============================================================================
# OsdagBridge — Chart Generation Module
# Generates high-resolution Matplotlib charts for Chapter 5.5 (Utilization Ratios)
# and Chapter 7 (Material Quantities).
# All figures use the centralized styling defined in styles.py.
# =============================================================================
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Tuple, Any

from osdagbridge.core.reports.styles import (
    apply_chart_theme,
    COLOR_PASS,
    COLOR_WARN,
    COLOR_FAIL,
    COLOR_REF_LINE,
    COLOR_BAR_STEEL,
    COLOR_BAR_CONCRETE,
    COLOR_BAR_REBAR,
    COLOR_OSDAG_GREEN,
)
from osdagbridge.core.utils.common import (
    KEY_DD_HAS_OVERHANG,
    KEY_DD_M_ULS_SAG,
    KEY_DD_MU_BOT,
    KEY_DD_M_ULS_HOG,
    KEY_DD_MU_TOP,
    KEY_DD_M_ULS_OH,
    KEY_DD_MU_OH,
    KEY_DD_PUNCH_VED,
    KEY_DD_VRD_C_MPA,
    KEY_DD_SHEAR_VED,
    KEY_DD_SHEAR_VRDC,
    KEY_DD_WK_BOT,
    KEY_DD_WK_TOP,
    KEY_DD_WK_OH,
    KEY_DD_WK_LIMIT,
    KEY_MP_ED_TYPE,
)

import sys

logger = logging.getLogger("osdagbridge.core.reports.charts")

# On Windows in Conda environments, ensure Library\bin is added for freetype/png DLLs
if os.name == "nt":
    lib_bin = os.path.join(sys.prefix, "Library", "bin")
    if os.path.isdir(lib_bin) and hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(lib_bin)
        except Exception:
            pass

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    logger.warning("matplotlib is not installed in the environment. Charts cannot be generated.")
    HAS_MATPLOTLIB = False


def _safe_float(val: Any) -> Optional[float]:
    """Safely convert a value to float; return None if invalid."""
    if val is None or val == "" or str(val).strip().upper() in {"N.A.", "N/A", "---"}:
        return None
    try:
        f = float(val)
        return f if not (f != f) else None  # avoid NaN
    except (ValueError, TypeError):
        return None


def _get_bar_color(ur: float) -> str:
    """Return color according to utilization ratio: Pass, Warning, or Fail."""
    if ur <= 0.90:
        return COLOR_PASS
    elif ur <= 1.00:
        return COLOR_WARN
    else:
        return COLOR_FAIL


# ── 1. Steel Plate Girder Utilization Chart ───────────────────────────────────

def generate_girder_utilization_chart(bridge: Any, output_dir: str) -> Optional[str]:
    """Generate horizontal bar chart for steel plate girder utilization ratios."""
    if not HAS_MATPLOTLIB:
        return None

    pg = (bridge.output_dict.get("design_results", {}) or {}).get("per_girder", {}) or {}
    if not pg:
        return None

    check_specs = [
        ("Moment Capacity (ULS)", {1}),
        ("Shear Capacity (ULS)", {2}),
        ("Lateral-Torsional Buckling", {5}),
        ("Vertical Deflection (SLS)", {13, 14}),
        ("Combined Stress (SLS)", {11}),
        ("Fatigue Assessment (SLS)", {8, 9}),
        ("Shear Stud Connectors", {16}),
    ]

    labels = []
    ratios = []

    for name, check_ids in check_specs:
        best_dcr = None
        for g, gd in pg.items():
            if str(g).startswith("EB"):
                continue
            # Check envelope checks
            for chk in (gd.get("checks") or []):
                if chk.get("check_id") in check_ids:
                    d = _safe_float(chk.get("dcr"))
                    if d is not None and (best_dcr is None or d > best_dcr):
                        best_dcr = d
            # Fallback to per_lc (e.g. deflection)
            if best_dcr is None:
                for _lc, _ld in (gd.get("per_lc") or {}).items():
                    if str(_lc).lower().startswith("envelope"):
                        continue
                    for _chk in (_ld.get("checks") or []):
                        if _chk.get("id") in check_ids:
                            d = _safe_float(_chk.get("dcr"))
                            if d is not None and (best_dcr is None or d > best_dcr):
                                best_dcr = d
        if best_dcr is not None:
            labels.append(name)
            ratios.append(best_dcr)

    if not ratios:
        return None

    fig, ax = apply_chart_theme(plt, figsize=(7.2, 3.8))
    y_pos = list(range(len(labels)))
    colors = [_get_bar_color(r) for r in ratios]

    bars = ax.barh(y_pos, ratios, height=0.55, color=colors, edgecolor="#444444", linewidth=0.5)
    ax.axvline(1.0, color=COLOR_REF_LINE, linestyle="--", linewidth=1.5, label="Permissible Limit (UR = 1.0)")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Utilization Ratio (UR = Demand / Capacity)")
    ax.set_title("Steel Plate Girders — Utilization Ratios", pad=12)

    max_x = max(1.2, max(ratios) * 1.18)
    ax.set_xlim(0, max_x)

    for bar, val in zip(bars, ratios):
        status_txt = "Pass" if val <= 1.0 else "Fail"
        ax.text(val + 0.02, bar.get_y() + bar.get_height() / 2, f"{val:.2f} ({status_txt})",
                va="center", ha="left", fontsize=8.5, fontweight="bold", color="#333333")

    ax.legend(loc="lower right", framealpha=0.9)
    plt.tight_layout()

    out_file = os.path.join(output_dir, "ur_steel_girders.png")
    fig.savefig(out_file, dpi=200)
    plt.close(fig)
    return out_file


# ── 2. Concrete Deck Slab Utilization Chart ───────────────────────────────────

def generate_deck_utilization_chart(bridge: Any, output_dir: str) -> Optional[str]:
    """Generate horizontal bar chart for concrete deck slab utilization ratios."""
    if not HAS_MATPLOTLIB:
        return None

    deck_rpt = bridge.output_dict.get("deck_report_values", {}) or {}
    if not deck_rpt:
        return None

    labels = []
    ratios = []

    def _add_check(label: str, dem_key: str, cap_key: str):
        dem = _safe_float(deck_rpt.get(dem_key))
        cap = _safe_float(deck_rpt.get(cap_key))
        if dem is not None and cap is not None and cap > 0:
            labels.append(label)
            ratios.append(dem / cap)

    _add_check("Sagging Flexure (Bottom Rebar)", KEY_DD_M_ULS_SAG, KEY_DD_MU_BOT)
    _add_check("Hogging Flexure (Top Rebar)", KEY_DD_M_ULS_HOG, KEY_DD_MU_TOP)

    if deck_rpt.get(KEY_DD_HAS_OVERHANG):
        _add_check("Cantilever Overhang Flexure", KEY_DD_M_ULS_OH, KEY_DD_MU_OH)

    _add_check("Punching Shear (IRC 112)", KEY_DD_PUNCH_VED, KEY_DD_VRD_C_MPA)
    _add_check("One-Way Shear (IRC 112)", KEY_DD_SHEAR_VED, KEY_DD_SHEAR_VRDC)

    # Crack width
    wks = []
    for wk_k in (KEY_DD_WK_BOT, KEY_DD_WK_TOP, KEY_DD_WK_OH if deck_rpt.get(KEY_DD_HAS_OVERHANG) else None):
        if wk_k:
            v = _safe_float(deck_rpt.get(wk_k))
            if v is not None:
                wks.append(v)
    wk_lim = _safe_float(deck_rpt.get(KEY_DD_WK_LIMIT))
    if wks and wk_lim is not None and wk_lim > 0:
        labels.append("Crack Width Limit (SLS)")
        ratios.append(max(wks) / wk_lim)

    if not ratios:
        return None

    fig, ax = apply_chart_theme(plt, figsize=(7.2, 3.5))
    y_pos = list(range(len(labels)))
    colors = [_get_bar_color(r) for r in ratios]

    bars = ax.barh(y_pos, ratios, height=0.55, color=colors, edgecolor="#444444", linewidth=0.5)
    ax.axvline(1.0, color=COLOR_REF_LINE, linestyle="--", linewidth=1.5, label="Permissible Limit (UR = 1.0)")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Utilization Ratio (UR = Demand / Capacity)")
    ax.set_title("Concrete Deck Slab — Utilization Ratios", pad=12)

    max_x = max(1.2, max(ratios) * 1.18)
    ax.set_xlim(0, max_x)

    for bar, val in zip(bars, ratios):
        status_txt = "Pass" if val <= 1.0 else "Fail"
        ax.text(val + 0.02, bar.get_y() + bar.get_height() / 2, f"{val:.2f} ({status_txt})",
                va="center", ha="left", fontsize=8.5, fontweight="bold", color="#333333")

    ax.legend(loc="lower right", framealpha=0.9)
    plt.tight_layout()

    out_file = os.path.join(output_dir, "ur_deck_slab.png")
    fig.savefig(out_file, dpi=200)
    plt.close(fig)
    return out_file


# ── 3. Cross Bracing Utilization Chart ───────────────────────────────────────

def generate_cb_utilization_chart(bridge: Any, output_dir: str) -> Optional[str]:
    """Generate horizontal bar chart for cross bracing utilization ratios."""
    if not HAS_MATPLOTLIB:
        return None

    pairs = bridge.get_cb_pairs()
    if not pairs:
        return None

    worst_comp_ur = None
    worst_tens_ur = None
    worst_slend_ratio = None

    for pair in pairs:
        for member in ("diagonal", "chord"):
            # Compression
            eff_c = _safe_float(bridge.get_cb_efficiency(pair, member, "compression"))
            if eff_c is not None and (worst_comp_ur is None or eff_c > worst_comp_ur):
                worst_comp_ur = eff_c
            # Tension
            eff_t = _safe_float(bridge.get_cb_efficiency(pair, member, "tension"))
            if eff_t is not None and (worst_tens_ur is None or eff_t > worst_tens_ur):
                worst_tens_ur = eff_t
            # Slenderness
            s = _safe_float(bridge.get_cb_slenderness(pair, member))
            if s is not None:
                lim = 400.0 if member == "chord" else 250.0
                ratio = s / lim
                if worst_slend_ratio is None or ratio > worst_slend_ratio:
                    worst_slend_ratio = ratio

    labels = []
    ratios = []

    if worst_comp_ur is not None:
        labels.append("Axial Compression (IS 800 Cl. 7)")
        ratios.append(worst_comp_ur)
    if worst_tens_ur is not None:
        labels.append("Axial Tension (IS 800 Cl. 6)")
        ratios.append(worst_tens_ur)
    if worst_slend_ratio is not None:
        labels.append("Slenderness Ratio (KL/r / Limit)")
        ratios.append(worst_slend_ratio)

    if not ratios:
        return None

    fig, ax = apply_chart_theme(plt, figsize=(7.2, 2.8))
    y_pos = list(range(len(labels)))
    colors = [_get_bar_color(r) for r in ratios]

    bars = ax.barh(y_pos, ratios, height=0.5, color=colors, edgecolor="#444444", linewidth=0.5)
    ax.axvline(1.0, color=COLOR_REF_LINE, linestyle="--", linewidth=1.5, label="Permissible Limit (UR = 1.0)")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Utilization Ratio (UR = Demand / Capacity)")
    ax.set_title("Cross Bracing — Governing Utilization Ratios", pad=12)

    max_x = max(1.2, max(ratios) * 1.18)
    ax.set_xlim(0, max_x)

    for bar, val in zip(bars, ratios):
        status_txt = "Pass" if val <= 1.0 else "Fail"
        ax.text(val + 0.02, bar.get_y() + bar.get_height() / 2, f"{val:.2f} ({status_txt})",
                va="center", ha="left", fontsize=8.5, fontweight="bold", color="#333333")

    ax.legend(loc="lower right", framealpha=0.9)
    plt.tight_layout()

    out_file = os.path.join(output_dir, "ur_cross_bracing.png")
    fig.savefig(out_file, dpi=200)
    plt.close(fig)
    return out_file


# ── 4. End Diaphragm Utilization Chart ───────────────────────────────────────

def generate_ed_utilization_chart(bridge: Any, output_dir: str) -> Optional[str]:
    """Generate horizontal bar chart for end diaphragm utilization ratios (if modelled)."""
    if not HAS_MATPLOTLIB:
        return None

    ed_type = ""
    for k, v in bridge.input_dict.items():
        if str(k).startswith(KEY_MP_ED_TYPE) and v:
            ed_type = str(v)
            break

    # If end diaphragm is of bracing type, it utilizes the bracing results
    if "brac" in ed_type.strip().lower():
        # Check if cross bracing results exist
        return generate_cb_utilization_chart(bridge, output_dir)

    # For rolled / welded end diaphragm, design checks are not yet computed by the engine
    logger.info("End diaphragm design is rolled/welded or not modelled; skipping chart generation.")
    return None


# ── 5. Chapter 7 Quantity Charts ─────────────────────────────────────────────

def generate_steel_tonnage_chart(quantities: dict, output_dir: str) -> Optional[str]:
    """Generate horizontal bar chart for structural steel tonnage breakdown."""
    if not HAS_MATPLOTLIB:
        return None

    items = [
        ("Steel Girders", quantities.get("steel_girders_wt_total")),
        ("Top Chords", quantities.get("bracing_top_wt_total")),
        ("Bottom Chords", quantities.get("bracing_bot_wt_total")),
        ("Diagonals", quantities.get("bracing_diag_wt_total")),
        ("Shear Studs", quantities.get("shear_studs_wt_total")),
        ("Crash Barrier", quantities.get("crash_barrier_wt_total")),
    ]

    labels = []
    weights = []

    for name, val in items:
        w = _safe_float(val)
        if w is not None and w > 0:
            labels.append(name)
            weights.append(w)

    if not weights:
        # Fallback if specific breakdown not present but girders exist
        gw = _safe_float(quantities.get("steel_girders_wt_total"))
        if gw is not None and gw > 0:
            labels = ["Steel Girders"]
            weights = [gw]
        else:
            return None

    fig, ax = apply_chart_theme(plt, figsize=(7.2, 3.4))
    y_pos = list(range(len(labels)))

    bars = ax.barh(y_pos, weights, height=0.55, color=COLOR_BAR_STEEL, edgecolor="#1A365D", linewidth=0.6)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Weight (Metric Tonnes, MT)")
    ax.set_title("Structural Steel Breakdown (Tonnage in MT)", pad=12)

    max_x = max(weights) * 1.2
    ax.set_xlim(0, max_x)

    for bar, val in zip(bars, weights):
        ax.text(val + (max_x * 0.015), bar.get_y() + bar.get_height() / 2, f"{val:.2f} MT",
                va="center", ha="left", fontsize=9, fontweight="bold", color="#1A365D")

    plt.tight_layout()

    out_file = os.path.join(output_dir, "chart_steel_tonnage.png")
    fig.savefig(out_file, dpi=200)
    plt.close(fig)
    return out_file


def generate_concrete_vs_rebar_chart(quantities: dict, output_dir: str) -> Optional[str]:
    """Generate bar chart comparing concrete deck volume to reinforcement steel weight."""
    if not HAS_MATPLOTLIB:
        return None

    conc_vol = _safe_float(quantities.get("concrete_deck_vol_total"))
    rebar_wt = _safe_float(quantities.get("rebar_deck_wt_total"))

    if conc_vol is None and rebar_wt is None:
        return None

    fig, ax = apply_chart_theme(plt, figsize=(7.0, 3.2))

    categories = ["Deck Concrete Volume", "Reinforcement Steel"]
    values = [conc_vol or 0.0, rebar_wt or 0.0]
    units = ["m³", "MT"]
    colors = [COLOR_BAR_CONCRETE, COLOR_BAR_REBAR]

    bars = ax.bar(categories, values, width=0.45, color=colors, edgecolor="#333333", linewidth=0.6)

    ax.set_ylabel("Quantity (m³ / MT)")
    ax.set_title("Concrete Deck Volume vs. Reinforcement Weight", pad=12)

    max_y = max(values) * 1.25 if max(values) > 0 else 10.0
    ax.set_ylim(0, max_y)

    for bar, val, unit in zip(bars, values, units):
        ax.text(bar.get_x() + bar.get_width() / 2, val + (max_y * 0.02), f"{val:.2f} {unit}",
                ha="center", va="bottom", fontsize=9.5, fontweight="bold", color="#222222")

    plt.tight_layout()

    out_file = os.path.join(output_dir, "chart_concrete_vs_rebar.png")
    fig.savefig(out_file, dpi=200)
    plt.close(fig)
    return out_file


# ── Master Chart Generation Orchestrator ─────────────────────────────────────

def generate_all_report_charts(bridge: Any, quantities: dict, output_dir: str) -> Dict[str, str]:
    """
    Generate all Chapter 5.5 and Chapter 7 charts.
    Returns a dictionary mapping chart identifiers to their relative/absolute file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = {}

    try:
        p = generate_girder_utilization_chart(bridge, output_dir)
        if p:
            results["ur_steel_girders"] = p.replace("\\", "/")
    except Exception as e:
        logger.warning("Failed to generate girder utilization chart: %s", e)

    try:
        p = generate_deck_utilization_chart(bridge, output_dir)
        if p:
            results["ur_deck_slab"] = p.replace("\\", "/")
    except Exception as e:
        logger.warning("Failed to generate deck utilization chart: %s", e)

    try:
        p = generate_cb_utilization_chart(bridge, output_dir)
        if p:
            results["ur_cross_bracing"] = p.replace("\\", "/")
    except Exception as e:
        logger.warning("Failed to generate cross bracing utilization chart: %s", e)

    try:
        p = generate_ed_utilization_chart(bridge, output_dir)
        if p:
            results["ur_end_diaphragm"] = p.replace("\\", "/")
    except Exception as e:
        logger.warning("Failed to generate end diaphragm utilization chart: %s", e)

    try:
        p = generate_steel_tonnage_chart(quantities, output_dir)
        if p:
            results["chart_steel_tonnage"] = p.replace("\\", "/")
    except Exception as e:
        logger.warning("Failed to generate steel tonnage chart: %s", e)

    try:
        p = generate_concrete_vs_rebar_chart(quantities, output_dir)
        if p:
            results["chart_concrete_vs_rebar"] = p.replace("\\", "/")
    except Exception as e:
        logger.warning("Failed to generate concrete vs rebar chart: %s", e)

    return results

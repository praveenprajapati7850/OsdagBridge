"""
Unit and integration tests for OsdagBridge Report Generator, Chapter Modules,
and Chart Generation.
Uses Python's standard unittest framework (strictly without pytest).
"""

import os
import shutil
import tempfile
import unittest

from osdagbridge.core.reports.styles import (
    COLOR_OSDAG_GREEN,
    get_latex_preamble,
    build_multipage_table_header,
)
from osdagbridge.core.reports.report_generator import (
    ReportMetadata,
    ReportOptions,
    ReportRequest,
    ReportPayload,
    ReportFigures,
    ReportDataBridge,
    preamble,
    build_report_payload,
    generate_report,
)
from osdagbridge.core.reports.chap2 import ch2_input_parameters
from osdagbridge.core.reports.chap3 import ch3_loads
from osdagbridge.core.reports.chap4 import ch4_analysis
from osdagbridge.core.reports.chap5 import ch5_design_checks
from osdagbridge.core.reports.chap7 import ch7_quantities
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.utils.codes.keyfile import t
from unittest.mock import patch
from osdagbridge.core.reports.charts import (
    generate_girder_utilization_chart,
    generate_deck_utilization_chart,
    generate_cb_utilization_chart,
    generate_steel_tonnage_chart,
    generate_concrete_vs_rebar_chart,
    generate_all_report_charts,
)
from osdagbridge.core.utils.common import (
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
    KEY_TS_DECK_THICKNESS,
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
)


class TestReportStyles(unittest.TestCase):
    """Test the centralized report styling module."""

    def test_theme_constants(self):
        self.assertEqual(COLOR_OSDAG_GREEN, "#91B014")

    def test_preamble_structure(self):
        tex = get_latex_preamble("Test Bridge", "JOB-101", "2026-11-07", "Rev 0")
        self.assertIn(r"\documentclass[12pt,a4paper]{report}", tex)
        self.assertIn("headheight=18pt", tex)
        self.assertIn("footskip=38pt", tex)
        self.assertIn(r"\definecolor{osdagGreen}{HTML}{91B014}", tex)
        self.assertIn(r"\fancypagestyle{main}", tex)
        self.assertIn(r"\fancypagestyle{plain}", tex)
        self.assertIn(r"\fancypagestyle{firstpage}", tex)
        self.assertIn(r"\newcolumntype{L}", tex)
        self.assertIn(r"\newcolumntype{C}", tex)
        self.assertIn(r"\newcolumntype{R}", tex)
        self.assertIn("Test Bridge", tex)
        self.assertIn("JOB-101", tex)

    def test_preamble_backward_compatibility(self):
        tex1 = preamble("Bridge Proj", "J01", "2026-11-07", "Rev 0")
        tex2 = get_latex_preamble("Bridge Proj", "J01", "2026-11-07", "Rev 0")
        self.assertEqual(tex1, tex2)

    def test_multipage_table_header_helper(self):
        header = build_multipage_table_header(
            col_spec=r"|C{2cm}|L{6cm}|R{3cm}|",
            headers=["ID", "Description", "Value"],
            caption="Sample Check Table",
            label="tab:sample"
        )
        self.assertIn(r"\begin{longtable}{|C{2cm}|L{6cm}|R{3cm}|}", header)
        self.assertIn(r"\caption{\textbf{Sample Check Table}}\label{tab:sample} \\", header)
        self.assertIn(r"\endfirsthead", header)
        self.assertIn(r"\endhead", header)
        self.assertIn(r"\endfoot", header)
        self.assertIn(r"\endlastfoot", header)
        self.assertIn("Continued from previous page", header)


class TestChapter3Loads(unittest.TestCase):
    """Test Chapter 3 loads and geometry tables refactoring."""

    def test_chapter3_vehicular_and_footway_separation(self):
        inputs = {
            KEY_SPAN: "30.0",
            "loads.lane_table_count": "2",
            "loads.wc_ld_vehicle_class.1": "Class 70R Wheeled",
            "loads.wc_ld_vehicle_class.2": "Class A",
            "loading.live_load.footpath_pressure.mode": "User-defined",
            "loading.live_load.footpath_pressure.value": "4.50",
            "loads.footway_width": "1.5",
            "loads.seismic_zone": "Zone IV",
            "loads.wind_speed": "44",
        }
        tex = ch3_loads(inputs)

        # Verify separation of tables
        self.assertIn("Vehicular Live Load Selection", tex)
        self.assertIn("Vehicular Dynamic, Braking, and Centrifugal Effects", tex)
        self.assertIn("Footway / Pedestrian Live Load", tex)

        # Verify repeated headers in Chapter 3 tables
        self.assertIn(r"\endfirsthead", tex)
        self.assertIn(r"\endhead", tex)
        self.assertIn(r"\endfoot", tex)
        self.assertIn(r"\endlastfoot", tex)

        # Verify IRC 6 provisions for braking force and centrifugal force
        self.assertIn("Longitudinal Braking Force", tex)
        self.assertIn("1.20 m above deck surface", tex)
        self.assertIn("No horizontal curvature modelled; bridge geometry has straight alignment per IRC 6 Cl. 212", tex)
        self.assertIn("Dynamic Impact Factor", tex)
        self.assertIn("Footway Loading Intensity", tex)
        self.assertIn("4.50 kN/m", tex)


class TestMultipageTableHeaders(unittest.TestCase):
    """Verify that all major chapter tables include longtable headers and continuation footers."""

    def test_multipage_headers_across_chapters(self):
        # Chapter 2
        md = ReportMetadata(
            project_name="Bridge",
            project_location="Delhi",
            designer="Engineer",
            client="Client",
            company="Company",
            job_number="J-1"
        )
        inputs = {KEY_SPAN: "25.0", KEY_TS_NO_OF_GIRDERS: "2"}
        ch2_tex = ch2_input_parameters(md, inputs, {})
        self.assertIn(r"\endfirsthead", ch2_tex)
        self.assertIn(r"\endhead", ch2_tex)
        self.assertIn(r"\endfoot", ch2_tex)
        self.assertIn(r"\endlastfoot", ch2_tex)

        # Chapter 4
        opts = ReportOptions(sections=["analysis"], include_figures=False, include_toc=True, include_pdf=True)
        payload = ReportPayload(
            metadata=md, options=opts, inputs=inputs,
            analysis_summary={
                'load_cases': {'DL': {'max_bm': 100.0, 'min_bm': 0.0, 'max_sf': 50.0, 'min_sf': -50.0}},
                'reactions': {'DL': {'R_left': 50.0, 'R_right': 50.0}}
            },
            design_checks=[], figures=ReportFigures(), log_entries=[], output_dict={}
        )
        bridge = ReportDataBridge({}, inputs, payload)
        ch4_tex = ch4_analysis(payload.analysis_summary, {}, bridge, 25.0)
        self.assertIn(r"\endfirsthead", ch4_tex)
        self.assertIn(r"\endhead", ch4_tex)

        # Chapter 7
        ch7_tex = ch7_quantities(inputs, {})
        self.assertIn(r"\endfirsthead", ch7_tex)
        self.assertIn(r"\endhead", ch7_tex)
        self.assertIn(r"\endfoot", ch7_tex)
        self.assertIn(r"\endlastfoot", ch7_tex)


class TestUtilizationAndQuantityCharts(unittest.TestCase):
    """Test Matplotlib chart generation for utilization ratios and material quantities."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_girder_utilization_chart(self):
        mock_output = {
            "design_results": {
                "per_girder": {
                    "G1": {
                        "checks": [
                            {"check_id": 1, "dcr": 0.82, "demand": 2400.0, "capacity": 2926.8},
                            {"check_id": 2, "dcr": 0.65, "demand": 450.0, "capacity": 692.3},
                            {"check_id": 5, "dcr": 0.74, "demand": 1200.0, "capacity": 1621.6},
                            {"check_id": 11, "dcr": 0.88, "demand": 210.0, "capacity": 238.6},
                            {"check_id": 16, "dcr": 0.55, "demand": 80.0, "capacity": 145.4},
                        ],
                        "per_lc": {
                            "LC1": {
                                "checks": [
                                    {"id": 13, "dcr": 0.60, "demand": 15.0, "capacity": 25.0}
                                ]
                            }
                        }
                    }
                }
            }
        }
        bridge = ReportDataBridge(mock_output, {KEY_SPAN: "25.0"}, None)
        chart_file = generate_girder_utilization_chart(bridge, self.tmp_dir)
        self.assertIsNotNone(chart_file)
        self.assertTrue(os.path.exists(chart_file))
        self.assertGreater(os.path.getsize(chart_file), 1000)

    def test_deck_utilization_chart(self):
        mock_output = {
            "deck_report_values": {
                KEY_DD_M_ULS_SAG: 75.0,
                KEY_DD_MU_BOT: 100.0,
                KEY_DD_M_ULS_HOG: 60.0,
                KEY_DD_MU_TOP: 95.0,
                KEY_DD_PUNCH_VED: 1.2,
                KEY_DD_VRD_C_MPA: 1.8,
                KEY_DD_SHEAR_VED: 90.0,
                KEY_DD_SHEAR_VRDC: 150.0,
                KEY_DD_WK_BOT: 0.15,
                KEY_DD_WK_TOP: 0.18,
                KEY_DD_WK_LIMIT: 0.25,
            }
        }
        bridge = ReportDataBridge(mock_output, {}, None)
        chart_file = generate_deck_utilization_chart(bridge, self.tmp_dir)
        self.assertIsNotNone(chart_file)
        self.assertTrue(os.path.exists(chart_file))
        self.assertGreater(os.path.getsize(chart_file), 1000)

    def test_cb_utilization_chart(self):
        mock_output = {
            "crossbracing_forces_dict": {
                "pairs": {
                    "G1-G2": {
                        "diag_tension_kN": 45.0,
                        "diag_compression_kN": -55.0,
                    }
                },
                "geometry": {"diagonal_length_m": 3.2}
            },
            "crossbracing_design_results": {
                "G1-G2": {
                    "diagonal": {
                        "compression": {"capacity_kN": 80.0, "efficiency": 0.688, "slenderness": 145.0},
                        "tension": {"capacity_kN": 120.0, "efficiency": 0.375, "slenderness": 145.0}
                    }
                }
            }
        }
        bridge = ReportDataBridge(mock_output, {}, None)
        chart_file = generate_cb_utilization_chart(bridge, self.tmp_dir)
        self.assertIsNotNone(chart_file)
        self.assertTrue(os.path.exists(chart_file))
        self.assertGreater(os.path.getsize(chart_file), 1000)

    def test_quantity_charts(self):
        quantities = {
            "steel_girders_wt_total": "28.50",
            "bracing_top_wt_total": "1.85",
            "bracing_bot_wt_total": "1.85",
            "bracing_diag_wt_total": "3.20",
            "shear_studs_wt_total": "0.45",
            "crash_barrier_wt_total": "1.10",
            "concrete_deck_vol_total": "45.00",
            "rebar_deck_wt_total": "5.40",
        }
        steel_chart = generate_steel_tonnage_chart(quantities, self.tmp_dir)
        self.assertIsNotNone(steel_chart)
        self.assertTrue(os.path.exists(steel_chart))
        self.assertGreater(os.path.getsize(steel_chart), 1000)

        conc_chart = generate_concrete_vs_rebar_chart(quantities, self.tmp_dir)
        self.assertIsNotNone(conc_chart)
        self.assertTrue(os.path.exists(conc_chart))
        self.assertGreater(os.path.getsize(conc_chart), 1000)

    def test_generate_all_report_charts_orchestration(self):
        bridge = ReportDataBridge({}, {}, None)
        quantities = {"steel_girders_wt_total": "25.0", "concrete_deck_vol_total": "40.0", "rebar_deck_wt_total": "4.8"}
        res = generate_all_report_charts(bridge, quantities, self.tmp_dir)
        self.assertIn("chart_steel_tonnage", res)
        self.assertIn("chart_concrete_vs_rebar", res)


class TestBrakingForce(unittest.TestCase):
    """Unit tests for IRC:6-2017 Clause 211.2 braking force calculation."""

    def test_braking_force_zero_and_negative_lanes(self):
        self.assertEqual(IRC6_2017.cl_211_2_braking_force(0), 0.0)
        self.assertEqual(IRC6_2017.cl_211_2_braking_force(-1), 0.0)
        self.assertEqual(IRC6_2017.cl_211_2_braking_force(None), 0.0)

    def test_braking_force_1_and_2_lanes(self):
        # 1 and 2 lanes: 20% of Class A total vehicle weight (55.4 t) = 11.08 t
        bf_1 = IRC6_2017.cl_211_2_braking_force(1)
        bf_2 = IRC6_2017.cl_211_2_braking_force(2)
        self.assertEqual(bf_1, 11.08)
        self.assertEqual(bf_2, 11.08)

    def test_braking_force_3_and_4_lanes(self):
        # 3 lanes: 11.08 + (3 - 2) * 5.0 = 16.08 t
        # 4 lanes: 11.08 + (4 - 2) * 5.0 = 21.08 t
        bf_3 = IRC6_2017.cl_211_2_braking_force(3)
        bf_4 = IRC6_2017.cl_211_2_braking_force(4)
        self.assertEqual(bf_3, 16.08)
        self.assertEqual(bf_4, 21.08)
        # Monotonicity check
        self.assertGreater(bf_4, bf_3)
        self.assertGreater(bf_3, IRC6_2017.cl_211_2_braking_force(2))

    def test_braking_force_units_consistency(self):
        # Class A sum divided by t must equal 55.4 t exactly
        sum_a = sum(IRC6_2017.cl_204_1_ClassA_vehicle()['wheel_loads'])
        weight_a_t = sum_a / t
        self.assertAlmostEqual(weight_a_t, 55.4, places=2)
        # 20% of Class A weight
        self.assertAlmostEqual(0.20 * weight_a_t, 11.08, places=3)

        # Class 70R sum divided by t must equal 100.0 t exactly
        sum_70r = sum(IRC6_2017.cl_204_1_Class70R_vehicle_wheel()['wheel_loads'])
        weight_70r_t = sum_70r / t
        self.assertAlmostEqual(weight_70r_t, 100.0, places=2)
        # 5% of Class 70R weight per lane over 2
        self.assertAlmostEqual(0.05 * weight_70r_t, 5.0, places=3)


class TestChapter3BrakingAndErrorHandling(unittest.TestCase):
    """Test Chapter 3 braking force rendering and transparent error handling."""

    def test_ch3_braking_force_rendering(self):
        inputs = {
            "typical_section.lane_details.lane_table_count": "2",
            KEY_SPAN: "25.0",
        }
        tex = ch3_loads(inputs)
        # 11.08 t * 9.81 = 108.69 kN
        self.assertIn("108.69 kN (11.08 tonnes for 2 lanes)", tex)

    def test_ch3_braking_force_carriageway_fallback(self):
        # Lane count missing, but carriageway width provided as 7.5 m (2 lanes)
        inputs = {
            "typical_section.carriageway_width": "7.5",
            KEY_SPAN: "25.0",
        }
        tex = ch3_loads(inputs)
        self.assertIn("108.69 kN (11.08 tonnes for 2 lanes)", tex)

    def test_ch3_braking_force_error_handling(self):
        inputs = {
            "typical_section.lane_details.lane_table_count": "2",
            KEY_SPAN: "25.0",
        }
        with patch.object(IRC6_2017, "cl_211_2_braking_force", side_effect=RuntimeError("Simulated engine error")):
            tex = ch3_loads(inputs)
            self.assertIn(r"\textcolor{failRed}{Calculation Error (Inspect engine log)}", tex)


class TestFullReportPDFIntegration(unittest.TestCase):
    """End-to-end integration test compiling full design report with charts to PDF."""

    def setUp(self):
        self.output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports_output")
        os.makedirs(self.output_dir, exist_ok=True)

    def test_full_report_generation_with_charts(self):
        req = ReportRequest(
            metadata=ReportMetadata(
                project_name="Complete Bridge Design Verification",
                project_location="Mumbai, Maharashtra",
                designer="Praveen Kumar",
                client="Ministry of Road Transport and Highways (MoRTH)",
                company="Indian Institute of Technology Bombay",
                job_number="FULL-2026-001",
                subtitle="Final Refactored Report",
                report_date="2026-11-07"
            ),
            options=ReportOptions(
                sections=["loads", "analysis", "design_checks", "drawings"],
                include_figures=True,
                include_toc=True,
                include_pdf=True
            ),
            output_dir=self.output_dir,
            file_stem="final_design_report"
        )

        inputs = {
            KEY_SPAN: "28.0",
            KEY_TS_NO_OF_GIRDERS: "2",
            "loads.lane_table_count": "2",
            "loads.wc_ld_vehicle_class.1": "Class 70R Wheeled",
            "loads.wc_ld_vehicle_class.2": "Class A",
            "loads.footway_live_load": "4.0",
            "loads.footway_width": "1.5",
            "loads.footway_load_type": "Pedestrian and Light Vehicle",
            "loads.seismic_zone": "Zone III",
            "loads.wind_speed": "39",
            "typical_section.overall_bridge_width": "8.5",
            KEY_TS_DECK_THICKNESS: "220",
            "member_properties.girder_details.section_input.web_depth": "1800",
            "member_properties.girder_details.section_input.web_thickness": "14",
            "member_properties.girder_details.section_input.top_flange_width": "450",
            "member_properties.girder_details.section_input.top_flange_thickness": "25",
            "member_properties.girder_details.section_input.bottom_flange_width": "500",
            "member_properties.girder_details.section_input.bottom_flange_thickness": "32",
        }

        outputs = {
            "design_results": {
                "per_girder": {
                    "G1": {
                        "checks": [
                            {"check_id": 1, "dcr": 0.84, "demand": 2800.0, "capacity": 3333.3, "demand_unit": "kN-m", "capacity_unit": "kN-m"},
                            {"check_id": 2, "dcr": 0.72, "demand": 520.0, "capacity": 722.2, "demand_unit": "kN", "capacity_unit": "kN"},
                            {"check_id": 5, "dcr": 0.78, "demand": 1400.0, "capacity": 1794.8, "demand_unit": "kN-m", "capacity_unit": "kN-m"},
                            {"check_id": 11, "dcr": 0.89, "demand": 215.0, "capacity": 241.5, "demand_unit": "MPa", "capacity_unit": "MPa"},
                            {"check_id": 8, "dcr": 0.62, "demand": 45.0, "capacity": 72.5, "demand_unit": "MPa", "capacity_unit": "MPa"},
                            {"check_id": 16, "dcr": 0.68, "demand": 95.0, "capacity": 139.7, "demand_unit": "kN", "capacity_unit": "kN"},
                        ],
                        "per_lc": {
                            "SLS-Deflection": {
                                "checks": [
                                    {"id": 13, "dcr": 0.70, "demand": 17.5, "capacity": 25.0}
                                ]
                            }
                        }
                    }
                }
            },
            "deck_report_values": {
                KEY_DD_HAS_OVERHANG: 1,
                KEY_DD_M_ULS_SAG: 82.5,
                KEY_DD_MU_BOT: 105.0,
                KEY_DD_M_ULS_HOG: 68.0,
                KEY_DD_MU_TOP: 98.0,
                KEY_DD_M_ULS_OH: 42.0,
                KEY_DD_MU_OH: 70.0,
                KEY_DD_PUNCH_VED: 1.35,
                KEY_DD_VRD_C_MPA: 1.80,
                KEY_DD_SHEAR_VED: 110.0,
                KEY_DD_SHEAR_VRDC: 165.0,
                KEY_DD_WK_BOT: 0.16,
                KEY_DD_WK_TOP: 0.19,
                KEY_DD_WK_OH: 0.14,
                KEY_DD_WK_LIMIT: 0.25,
            },
            "crossbracing_forces_dict": {
                "pairs": {
                    "G1-G2": {
                        "diag_tension_kN": 52.0,
                        "diag_compression_kN": -64.0,
                    }
                },
                "geometry": {"diagonal_length_m": 3.4}
            },
            "crossbracing_design_results": {
                "G1-G2": {
                    "diagonal": {
                        "compression": {"capacity_kN": 92.0, "efficiency": 0.696, "slenderness": 150.0},
                        "tension": {"capacity_kN": 135.0, "efficiency": 0.385, "slenderness": 150.0}
                    }
                }
            },
            "analysis_summary": {
                "load_cases": {
                    "DL": {"max_bm": 1250.0, "min_bm": 0.0, "max_sf": 180.0, "min_sf": -180.0},
                    "SIDL": {"max_bm": 650.0, "min_bm": 0.0, "max_sf": 95.0, "min_sf": -95.0},
                    "LL": {"max_bm": 2100.0, "min_bm": 0.0, "max_sf": 310.0, "min_sf": -310.0},
                },
                "reactions": {
                    "DL": {"R_left": 180.0, "R_right": 180.0},
                    "SIDL": {"R_left": 95.0, "R_right": 95.0},
                    "LL": {"R_left": 310.0, "R_right": 310.0},
                }
            },
            "design_checks": [],
            "design_log": [
                "Preliminary Sizing: Complete",
                "Dead and Superimposed Dead Load Analysis: Pass",
                "Live Load Placement and Enveloping: Pass",
                "Plate Girder Flexural and Shear Design: Pass (IRC 22 / IS 800)",
                "Cross Bracing Member Design: Pass (IS 800 Cl. 6, 7)",
                "Reinforced Concrete Deck Slab Design: Pass (IRC 112)",
                "Serviceability and Fatigue Checks: Pass",
                "Bill of Quantities Calculation: Complete"
            ]
        }

        payload = build_report_payload(req, inputs, outputs)
        res = generate_report(payload, req)

        self.assertIsNotNone(res.tex_path, "TeX source was not generated")
        self.assertTrue(os.path.exists(res.tex_path), f"TeX file does not exist at {res.tex_path}")

        # Verify TeX contents
        with open(res.tex_path, "r", encoding="utf-8") as f:
            tex_content = f.read()

        # Check repeated table headers
        self.assertIn(r"\endfirsthead", tex_content)
        self.assertIn(r"\endhead", tex_content)
        self.assertIn(r"\endfoot", tex_content)
        self.assertIn(r"\endlastfoot", tex_content)

        # Check Chapter 3 separation
        self.assertIn("Vehicular Live Load Selection", tex_content)
        self.assertIn("Footway / Pedestrian Live Load", tex_content)

        # Check Chapter 5.5 utilization charts
        self.assertIn("Component Utilization Charts", tex_content)
        self.assertIn("images/ur_steel_girders.png", tex_content)
        self.assertIn("images/ur_deck_slab.png", tex_content)
        self.assertIn("images/ur_cross_bracing.png", tex_content)

        # Check Chapter 7 quantity charts
        self.assertIn("Material Quantity Visualizations", tex_content)
        self.assertIn("images/chart_steel_tonnage.png", tex_content)
        self.assertIn("images/chart_concrete_vs_rebar.png", tex_content)

        # Verify image portability: check that output images dir exists with exported assets
        dest_images = os.path.join(self.output_dir, "images")
        self.assertTrue(os.path.exists(dest_images), "Images directory was not copied to output_dir")
        self.assertTrue(os.path.exists(os.path.join(dest_images, "ur_steel_girders.png")))
        self.assertTrue(os.path.exists(os.path.join(dest_images, "chart_steel_tonnage.png")))

        # Check PDF compilation
        if res.pdf_path:
            self.assertTrue(os.path.exists(res.pdf_path), f"PDF file does not exist at {res.pdf_path}")
            pdf_size = os.path.getsize(res.pdf_path)
            self.assertGreater(pdf_size, 50000, f"PDF size {pdf_size} bytes is unusually small")
            print(f"Generated Final PDF: {res.pdf_path} ({pdf_size} bytes)")


if __name__ == "__main__":
    unittest.main()

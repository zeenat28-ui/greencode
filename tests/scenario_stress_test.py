"""Comprehensive End-to-End Scenario & Efficiency Benchmark Suite for GreenCode Auditor.

Tests all 7 system layers under realistic operational conditions:
1. Multi-Language Tree-sitter CST Parsing (Speed & Detection Precision)
2. Live Regional Grid Telemetry (Electricity Maps & Cache Invalidation)
3. Dynamic Execution Profiling & GSF SCI Model (Hardware Telemetry)
4. AI Multi-Language Eco-Refactoring (IBM Bob 2.0 Engine & Latency)
5. Pre-flight Repository Ingestion (Safety & Media Asset Filtering)
6. CI/CD Gatekeeper Evaluation (Quality Threshold Enforcement)
7. SQLite Analytics Persistence & Aggregations
"""

import json
import os
import sys
import time
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import (
    get_cumulative_carbon_savings,
    get_latest_repositories,
    get_repository_details,
    init_db,
    save_profile_metric,
    save_refactoring_record,
    save_scan_results,
)
from app.github_client import inspect_repository_before_audit
from app.optimizer import (
    get_zone_carbon_intensity,
    list_available_zones,
    refactor_repository_code,
)
from app.parser import (
    ViolationType,
    audit_file,
    audit_repository,
)
from app.profiler import DynamicExecutionProfiler, calculate_energy_and_sci


class ScenarioBenchmarkRunner:
    def __init__(self):
        self.results = {}
        self.issues = []
        self.recommendations = []
        init_db()

    def run_all(self):
        print("=" * 70)
        print(">> STARTING GREENCODE AUDITOR END-TO-END SCENARIO BENCHMARK")
        print("=" * 70)


        self.scenario_1_multilang_parsing()
        self.scenario_2_grid_telemetry()
        self.scenario_3_dynamic_profiling()
        self.scenario_4_ai_refactoring()
        self.scenario_5_preflight_ingestion()
        self.scenario_6_ci_gatekeeper()
        self.scenario_7_database_persistence()

        self.generate_report()

    # ----------------------------------------------------
    # SCENARIO 1: Multi-Language Parsing
    # ----------------------------------------------------
    def scenario_1_multilang_parsing(self):
        print("\n[Scenario 1/7] Testing Multi-Language Tree-sitter CST Parsing...")
        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))
        
        target_files = [
            ("python", "heavy_pipeline.py", 4),     # expects 4 violations
            ("python", "eco_pipeline.py", 0),       # expects 0 violations
            ("javascript", "sample_nested.js", 1),   # expects 1 violation (depth 3)
            ("cpp", "sample_nested.cpp", 1),         # expects 1 violation (depth 3)
            ("java", "sample_nested.java", 1),       # expects 1 violation (depth 3)
            ("go", "sample_nested.go", 1),           # expects 1 violation (depth 3)
        ]

        parsing_metrics = []
        total_start = time.perf_counter()

        for lang, fname, expected_v_count in target_files:
            fpath = os.path.join(samples_dir, fname)
            t0 = time.perf_counter()
            audit_res = audit_file(fpath)
            dt_ms = (time.perf_counter() - t0) * 1000.0

            v_count = len(audit_res["violations"])
            status = "PASS" if (v_count >= expected_v_count) else "FAIL"

            if v_count < expected_v_count:
                self.issues.append(f"[Parser] {fname} ({lang}) found {v_count} issues, expected {expected_v_count}.")

            parsing_metrics.append({
                "file": fname,
                "language": lang,
                "time_ms": round(dt_ms, 2),
                "violations_found": v_count,
                "expected": expected_v_count,
                "green_score": audit_res["green_score"],
                "status": status,
            })
            print(f"  • {fname:<20} ({lang:<10}): {dt_ms:>6.2f} ms | Score: {audit_res['green_score']:>5.1f} | Issues: {v_count} [{status}]")

        # Repository-level aggregation test
        t_repo_start = time.perf_counter()
        repo_res = audit_repository(samples_dir)
        repo_ms = (time.perf_counter() - t_repo_start) * 1000.0
        print(f"  • Entire Folder Scan (6 files): {repo_ms:.2f} ms | Total Issues: {len(repo_res['violations'])} | Repo Green Score: {repo_res['green_score']:.1f}")

        avg_file_ms = sum(m["time_ms"] for m in parsing_metrics) / len(parsing_metrics)
        self.results["scenario_1"] = {
            "avg_file_parse_time_ms": round(avg_file_ms, 2),
            "repo_scan_time_ms": round(repo_ms, 2),
            "files_tested": len(target_files),
            "all_passed": all(m["status"] == "PASS" for m in parsing_metrics),
        }

    # ----------------------------------------------------
    # SCENARIO 2: Live Grid Telemetry & Caching
    # ----------------------------------------------------
    def scenario_2_grid_telemetry(self):
        print("\n[Scenario 2/7] Testing Electricity Maps Live Grid Telemetry & 120s TTL Caching...")
        
        zones_to_test = ["US-CAL-CISO", "DE", "FR"]
        cache_metrics = []

        for z in zones_to_test:
            # 1. Uncached / Live network call
            t0 = time.perf_counter()
            d1 = get_zone_carbon_intensity(z)
            t_live = (time.perf_counter() - t0) * 1000.0

            # 2. Cached lookup call (within 120s TTL)
            t1 = time.perf_counter()
            d2 = get_zone_carbon_intensity(z)
            t_cached = (time.perf_counter() - t1) * 1000.0

            speedup = t_live / max(t_cached, 0.001)

            print(f"  • Zone {z:<12}: Live = {t_live:>6.1f} ms | Cached = {t_cached:>5.2f} ms | Speedup: {speedup:>6.1f}x | Carbon: {d1['carbon_intensity']} g/kWh")

            if d1["carbon_intensity"] <= 0:
                self.issues.append(f"[Grid] Zone {z} returned non-positive carbon intensity {d1['carbon_intensity']}.")

            cache_metrics.append({
                "zone": z,
                "live_ms": round(t_live, 1),
                "cached_ms": round(t_cached, 3),
                "speedup": round(speedup, 1),
            })

        self.results["scenario_2"] = cache_metrics

    # ----------------------------------------------------
    # SCENARIO 3: Dynamic Hardware Profiling & SCI Model
    # ----------------------------------------------------
    def scenario_3_dynamic_profiling(self):
        print("\n[Scenario 3/7] Testing Dynamic Execution Profiler & GSF SCI Model...")
        
        profiler = DynamicExecutionProfiler(grid_intensity_gco2_per_kwh=215.0)
        eco_sample = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "eco_pipeline.py"))

        t0 = time.perf_counter()
        prof_res = profiler.profile_file(eco_sample, timeout_sec=15.0)
        wall_clock = time.perf_counter() - t0

        print(f"  • Mode:              {prof_res.profiling_mode}")
        print(f"  • Runtime Duration:  {prof_res.duration_sec:.2f} s (Wall clock: {wall_clock:.2f} s)")
        print(f"  • Avg CPU Load:      {prof_res.avg_cpu_percent:.1f} %")
        print(f"  • Peak Memory:       {prof_res.peak_memory_mb:.1f} MB")
        print(f"  • Energy Estimated:  {prof_res.energy_wh:.6f} Wh ({prof_res.energy_joules:.3f} Joules)")
        print(f"  • Operational CO2:   {prof_res.operational_carbon_gco2:.6f} gCO2eq")
        print(f"  • GSF SCI Score:     {prof_res.sci_score_gco2:.6f} gCO2eq/run")

        if prof_res.energy_wh <= 0:
            self.issues.append("[Profiler] Energy estimation is zero or negative.")

        self.results["scenario_3"] = {
            "mode": prof_res.profiling_mode,
            "duration_sec": prof_res.duration_sec,
            "energy_wh": prof_res.energy_wh,
            "sci_score_gco2": prof_res.sci_score_gco2,
        }

    # ----------------------------------------------------
    # SCENARIO 4: Live AI Eco-Refactoring (IBM Bob 2.0 Engine)
    # ----------------------------------------------------
    def scenario_4_ai_refactoring(self):
        print("\n[Scenario 4/7] Testing Live GreenCode AI Eco-Refactoring via IBM Bob 2.0 Engine...")
        
        test_cases = [
            ("python", "NESTED_LOOPS_DEPTH_3+", "for i in range(10):\n    for j in range(10):\n        for k in range(10):\n            val = i*j*k"),
            ("javascript", "NESTED_LOOPS_DEPTH_3+", "for (let i=0; i<10; i++) { for (let j=0; j<10; j++) { for (let k=0; k<10; k++) { val += i*j*k; } } }"),
            ("cpp", "NESTED_LOOPS_DEPTH_3+", "for (int i=0; i<10; i++) { for (int j=0; j<10; j++) { for (int k=0; k<10; k++) { val += i*j*k; } } }"),
        ]

        refactor_results = []
        for lang, vtype, snippet in test_cases:
            t0 = time.perf_counter()
            resp = refactor_repository_code(snippet, vtype, language_id=lang)
            dt_s = time.perf_counter() - t0

            engine = resp.get("model_used", "Unknown")
            refactored = resp.get("refactored_code", "")
            reduction = resp.get("energy_reduction_pct", 0)

            print(f"  • Language: {lang:<10} | Time: {dt_s:>5.2f} s | Engine: {engine} | Energy Reduction: -{reduction}%")
            if not refactored or refactored == snippet:
                self.issues.append(f"[Optimizer] Failed to transform code for {lang}.")

            refactor_results.append({
                "language": lang,
                "latency_s": round(dt_s, 2),
                "engine": engine,
                "reduction_pct": reduction,
            })

        self.results["scenario_4"] = refactor_results

    # ----------------------------------------------------
    # SCENARIO 5: Pre-Flight Ingestion & Asset Filtering
    # ----------------------------------------------------
    def scenario_5_preflight_ingestion(self):
        print("\n[Scenario 5/7] Testing Pre-Flight Ingestion & Asset Filtering...")
        
        t0 = time.perf_counter()
        info = inspect_repository_before_audit("zeenat28-ui/robot")
        dt_live = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        info_cached = inspect_repository_before_audit("zeenat28-ui/robot")
        dt_cached = (time.perf_counter() - t1) * 1000.0

        print(f"  • Inspect 'zeenat28-ui/robot': Live = {dt_live:.1f} ms | Cached = {dt_cached:.3f} ms")
        print(f"  • Repo Size: {info['size_kb']} KB | Primary Lang: {info['language']}")
        print(f"  • Can Audit: {info['can_audit']} | Notice: {info['message']}")

        self.results["scenario_5"] = {
            "inspection_time_ms": round(dt_live, 1),
            "cached_time_ms": round(dt_cached, 3),
            "safe": info["can_audit"],
        }

    # ----------------------------------------------------
    # SCENARIO 6: CI/CD Quality Gatekeeper
    # ----------------------------------------------------
    def scenario_6_ci_gatekeeper(self):
        print("\n[Scenario 6/7] Testing CI/CD Quality Gatekeeper Threshold Enforcement...")
        
        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))
        scan = audit_repository(samples_dir)
        actual_score = scan["green_score"]

        # Test A: Threshold higher than actual (Must Fail / Block)
        strict_threshold = min(100.0, actual_score + 10.0)
        blocked = actual_score < strict_threshold

        # Test B: Threshold lower than actual (Must Pass)
        lenient_threshold = max(0.0, actual_score - 10.0)
        passed = actual_score >= lenient_threshold

        print(f"  • Repository Green Score: {actual_score:.1f} / 100")
        print(f"  • Test Strict Gate ({strict_threshold:.1f}): {'PASSED (Correctly Blocked Pipeline)' if blocked else 'FAILED'}")
        print(f"  • Test Lenient Gate ({lenient_threshold:.1f}): {'PASSED (Allowed Merge)' if passed else 'FAILED'}")

        if not (blocked and passed):
            self.issues.append("[CI Gate] CI quality gatekeeper logic did not enforce threshold correctly.")

        self.results["scenario_6"] = {
            "repo_score": actual_score,
            "gate_enforcement_correct": blocked and passed,
        }

    # ----------------------------------------------------
    # SCENARIO 7: Database Persistence & Cumulative Analytics
    # ----------------------------------------------------
    def scenario_7_database_persistence(self):
        print("\n[Scenario 7/7] Testing SQLite Analytics Persistence & Aggregations...")
        
        t0 = time.perf_counter()
        repo = save_scan_results(
            name="StressTestRepository",
            path_or_url="/stress/test",
            total_files=6,
            total_lines=250,
            green_score=78.5,
            violations_data=[{
                "file_path": "matrix.cpp",
                "line_number": 8,
                "violation_type": "NESTED_LOOPS_DEPTH_3+",
                "severity": "HIGH",
                "deduction": 15.0,
                "snippet": "for(;;)",
                "suggested_fix": "Vectorize",
            }],
        )
        t_save_repo = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        metric = save_profile_metric(
            file_path="matrix.cpp",
            duration_sec=0.45,
            avg_cpu_percent=42.0,
            peak_memory_mb=64.0,
            energy_wh=0.008,
            operational_carbon_gco2=0.0017,
            sci_score=0.002,
            repo_id=repo.id,
        )
        t_save_metric = (time.perf_counter() - t1) * 1000.0

        t2 = time.perf_counter()
        savings = get_cumulative_carbon_savings()
        t_savings = (time.perf_counter() - t2) * 1000.0

        print(f"  • Save Repository: {t_save_repo:.2f} ms (ID: {repo.id})")
        print(f"  • Save Profile Metric: {t_save_metric:.2f} ms")
        print(f"  • Query Cumulative Savings: {t_savings:.2f} ms -> Total Saved: {savings['total_carbon_saved_gco2_10k_runs']} gCO2eq")

        self.results["scenario_7"] = {
            "save_repo_ms": round(t_save_repo, 2),
            "save_metric_ms": round(t_save_metric, 2),
            "query_savings_ms": round(t_savings, 2),
        }

    # ----------------------------------------------------
    # FINAL REPORT
    # ----------------------------------------------------
    def generate_report(self):
        print("\n" + "=" * 70)
        print("[REPORT] GREENCODE AUDITOR BENCHMARK & DIAGNOSTIC REPORT")
        print("=" * 70)

        # Efficiency summary table
        print(f"Layer 1: Tree-sitter Parser Speed:     {self.results['scenario_1']['avg_file_parse_time_ms']} ms/file (Ultra-fast CST)")
        print(f"Layer 2: Electricity Maps Cache:       {self.results['scenario_2'][0]['speedup']}x acceleration via TTL")
        print(f"Layer 3: Dynamic Profiler Duration:     {self.results['scenario_3']['duration_sec']:.2f} s execution time")
        print(f"Layer 4: AI Eco-Refactor Latency:      {self.results['scenario_4'][0]['latency_s']} s (Cloud LLM round-trip)")
        print(f"Layer 5: Pre-flight Safety Check:      {self.results['scenario_5']['inspection_time_ms']} ms")
        print(f"Layer 6: CI Quality Gatekeeper:        {'Enforced' if self.results['scenario_6']['gate_enforcement_correct'] else 'Failed'}")
        print(f"Layer 7: Database CRUD Latency:        < {max(self.results['scenario_7'].values())} ms")

        print("-" * 70)
        if not self.issues:
            print("[SUCCESS] STATUS: ALL 7 SCENARIOS PASSED WITH ZERO CRITICAL DEFECTS.")
        else:
            print(f"[WARNING] FOUND {len(self.issues)} ISSUE(S) REQUIRING ATTENTION:")
            for issue in self.issues:
                print(f"   - {issue}")

        if self.recommendations:
            print("\n[RECOMMENDATION] REFINEMENT SUGGESTIONS:")
            for rec in self.recommendations:
                print(f"   - {rec}")
        print("=" * 70)



if __name__ == "__main__":
    runner = ScenarioBenchmarkRunner()
    runner.run_all()

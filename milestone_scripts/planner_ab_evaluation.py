"""
Planner A/B Evaluation - Compare deterministic vs tool-calling planners.
Generates a combined report and optional blind A/B files for human evaluation.
"""
import sys
from pathlib import Path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / '_prod'))
sys.path.insert(0, str(Path(__file__).parent))

import argparse
import csv
import json
import os
import random
import re
from datetime import datetime
from typing import Dict, List, Tuple

from agent_orchestrator import AgentOrchestrator
from database_utils import DatabaseManager
from test_cases import TEST_CASES


FORBIDDEN_FIELDS = {
    "EmailAddress",
    "Phone",
    "AddressLine1",
    "AddressLine2",
    "SalesQuota",
    "SalesQuotaDate",
    "LoginID",
    "NationalIDNumber",
}


def _normalize_table_name(name: str) -> str:
    cleaned = name.strip().strip("[]").lower()
    if "." in cleaned:
        cleaned = cleaned.split(".")[-1]
    return cleaned


def extract_tables(sql: str) -> List[str]:
    if not sql:
        return []
    pattern = re.compile(r"\b(from|join)\s+([A-Za-z0-9_\.\[\]]+)", re.IGNORECASE)
    matches = pattern.findall(sql)
    return [match[1] for match in matches]


def evaluate_result(
    result: Dict,
    expected_tables: List[str],
    known_tables: List[str],
) -> Dict:
    sql = result.get("sql_query") or ""
    tables = extract_tables(sql)

    expected_norm = {_normalize_table_name(t) for t in expected_tables}
    table_norm = {_normalize_table_name(t) for t in tables}

    expected_hits = len(expected_norm & table_norm)
    table_coverage = expected_hits / len(expected_norm) if expected_norm else 0.0

    known_norm = {_normalize_table_name(t) for t in known_tables}
    unknown_tables = sorted(t for t in table_norm if t not in known_norm)

    privacy_violations = [
        field for field in FORBIDDEN_FIELDS if field.lower() in sql.lower()
    ]

    plan_steps = result.get("plan", [])
    completed_steps = [s for s in plan_steps if s.get("status") == "completed"]
    required_steps = {"Generate SQL", "Validate SQL", "Execute SQL"}
    completed_names = {s.get("name") for s in completed_steps}
    plan_complete = required_steps.issubset(completed_names)

    tokens_used = result.get("tokens_used") or {}

    return {
        "success": result.get("success", False),
        "table_coverage": round(table_coverage, 3),
        "unknown_tables": unknown_tables,
        "privacy_violations": privacy_violations,
        "plan_complete": plan_complete,
        "latency_seconds": round(result.get("total_time", 0.0), 3),
        "sql_latency_seconds": round(result.get("sql_generation_time", 0.0), 3),
        "total_tokens": tokens_used.get("total_tokens", 0),
        "input_tokens": tokens_used.get("input_tokens", 0),
        "output_tokens": tokens_used.get("output_tokens", 0),
        "row_count": result.get("row_count", 0),
        "errors": result.get("errors", []),
    }


def run_mode(
    planner_mode: str,
    test_cases: List[Dict],
    use_rag: bool = True,
    enable_visualization: bool = False,
    enable_vision: bool = False,
) -> List[Dict]:
    orchestrator = AgentOrchestrator(
        use_rag=use_rag,
        enable_visualization=enable_visualization,
        enable_vision=enable_vision,
        planner_mode=planner_mode,
    )

    db = DatabaseManager()
    db.connect()
    known_tables = db.get_table_list()
    db.disconnect()

    results = []
    for test_case in test_cases:
        query = test_case["natural_language"]
        expected_tables = test_case["expected_tables"]

        raw_result = orchestrator.process_query(query, planner_mode=planner_mode)
        metrics = evaluate_result(raw_result, expected_tables, known_tables)

        results.append(
            {
                "test_id": test_case["id"],
                "query": query,
                "expected_tables": expected_tables,
                "planner_mode": planner_mode,
                "sql_query": raw_result.get("sql_query"),
                "metrics": metrics,
            }
        )

    orchestrator.shutdown()
    return results


def summarize(results: List[Dict]) -> Dict:
    total = len(results)
    successes = sum(1 for r in results if r["metrics"]["success"])
    plan_complete = sum(1 for r in results if r["metrics"]["plan_complete"])

    avg_latency = sum(r["metrics"]["latency_seconds"] for r in results) / total
    avg_sql_latency = sum(r["metrics"]["sql_latency_seconds"] for r in results) / total
    avg_tokens = sum(r["metrics"]["total_tokens"] for r in results) / total
    avg_table_coverage = sum(r["metrics"]["table_coverage"] for r in results) / total

    privacy_violations = sum(
        1 for r in results if r["metrics"]["privacy_violations"]
    )
    unknown_tables = sum(1 for r in results if r["metrics"]["unknown_tables"])

    return {
        "total_cases": total,
        "success_rate": round(successes / total, 3),
        "plan_complete_rate": round(plan_complete / total, 3),
        "avg_latency_seconds": round(avg_latency, 3),
        "avg_sql_latency_seconds": round(avg_sql_latency, 3),
        "avg_total_tokens": round(avg_tokens, 1),
        "avg_table_coverage": round(avg_table_coverage, 3),
        "privacy_violation_rate": round(privacy_violations / total, 3),
        "unknown_table_rate": round(unknown_tables / total, 3),
    }


def save_ab_files(
    deterministic_results: List[Dict],
    tool_results: List[Dict],
    output_dir: str,
) -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    blind_path = os.path.join(output_dir, f"planner_ab_blind_{timestamp}.csv")
    key_path = os.path.join(output_dir, f"planner_ab_key_{timestamp}.csv")

    blind_rows = []
    key_rows = []

    tool_by_id = {r["test_id"]: r for r in tool_results}
    for det in deterministic_results:
        test_id = det["test_id"]
        tool = tool_by_id[test_id]

        if random.random() < 0.5:
            a_label = "deterministic"
            b_label = "tool_calling"
            a_sql = det.get("sql_query")
            b_sql = tool.get("sql_query")
        else:
            a_label = "tool_calling"
            b_label = "deterministic"
            a_sql = tool.get("sql_query")
            b_sql = det.get("sql_query")

        blind_rows.append(
            {
                "test_id": test_id,
                "query": det["query"],
                "output_a_sql": a_sql,
                "output_b_sql": b_sql,
            }
        )
        key_rows.append(
            {
                "test_id": test_id,
                "output_a": a_label,
                "output_b": b_label,
            }
        )

    with open(blind_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["test_id", "query", "output_a_sql", "output_b_sql"],
        )
        writer.writeheader()
        writer.writerows(blind_rows)

    with open(key_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["test_id", "output_a", "output_b"])
        writer.writeheader()
        writer.writerows(key_rows)

    return {"blind": blind_path, "key": key_path}


def main():
    parser = argparse.ArgumentParser(
        description="Compare deterministic vs tool-calling planners."
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Limit the number of test cases (default: all)",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Randomly sample test cases when used with --max-cases",
    )
    args = parser.parse_args()

    output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)

    test_cases = TEST_CASES
    if args.max_cases is not None:
        if args.sample and args.max_cases < len(TEST_CASES):
            test_cases = random.sample(TEST_CASES, args.max_cases)
        else:
            test_cases = TEST_CASES[: args.max_cases]

    deterministic_results = run_mode("deterministic", test_cases)
    tool_results = run_mode("tool_calling", test_cases)

    summary = {
        "timestamp": datetime.now().isoformat(),
        "deterministic": summarize(deterministic_results),
        "tool_calling": summarize(tool_results),
    }

    summary["delta"] = {
        key: round(summary["tool_calling"][key] - summary["deterministic"][key], 3)
        for key in summary["tool_calling"].keys()
        if isinstance(summary["tool_calling"][key], (int, float))
    }

    report = {
        "summary": summary,
        "deterministic_results": deterministic_results,
        "tool_calling_results": tool_results,
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(output_dir, f"planner_ab_report_{timestamp}.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    ab_files = save_ab_files(deterministic_results, tool_results, output_dir)

    print("Planner A/B evaluation complete")
    print(f"Report: {report_path}")
    print(f"Blind A/B file: {ab_files['blind']}")
    print(f"A/B key file: {ab_files['key']}")


if __name__ == "__main__":
    main()

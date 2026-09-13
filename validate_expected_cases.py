from __future__ import annotations

import csv
import json
from pathlib import Path


PROJECT_DIRECTORY = Path(__file__).resolve().parent
VALIDATION_DIRECTORY = PROJECT_DIRECTORY / "validation"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def retained_edges(result_path: Path) -> set[tuple[str, str, str, str]]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    return {
        (
            str(row["donor_model_id"]),
            str(row["precursor_id"]),
            str(row["recipient_model_id"]),
            str(row["final_target_id"]),
        )
        for row in result.get("rows", [])
        if row.get("decision") == "Keep"
    }


def compare_expected_cases() -> list[dict[str, str]]:
    comparisons: list[dict[str, str]] = []
    for case_table in sorted(
        (VALIDATION_DIRECTORY / "cases").glob("*/config/expected_result.tsv")
    ):
        for case in read_tsv(case_table):
            expected_edge = (
                case["donor_model_id"],
                case["precursor_id"],
                case["recipient_model_id"],
                case["final_target_id"],
            )
            result_path = PROJECT_DIRECTORY / case["result_json"]
            observed = retained_edges(result_path)
            comparisons.append(
                {
                    "case_id": case["case_id"],
                    "expected": "edge_present",
                    "observed": (
                        "edge_present" if expected_edge in observed else "edge_absent"
                    ),
                    "pass": "PASS" if expected_edge in observed else "FAIL",
                }
            )

    for contrast_path in sorted(
        (VALIDATION_DIRECTORY / "cases").glob(
            "*/config/expected_contrasts.tsv"
        )
    ):
        case_directory = contrast_path.parents[1]
        result_paths = sorted((case_directory / "results").glob("*.json"))
        if len(result_paths) != 1:
            raise ValueError(
                f"Expected one saved JSON result for {case_directory.name}; "
                f"found {len(result_paths)}."
            )
        observed = retained_edges(result_paths[0])
        for contrast in read_tsv(contrast_path):
            expected_edge = (
                contrast["donor_model_id"],
                contrast["precursor_id"],
                contrast["consumer_model_id"],
                contrast["target_id"],
            )
            observed_result = (
                "edge_present" if expected_edge in observed else "edge_absent"
            )
            comparisons.append(
                {
                    "case_id": contrast["case_id"],
                    "expected": contrast["expected_result"],
                    "observed": observed_result,
                    "pass": (
                        "PASS"
                        if observed_result == contrast["expected_result"]
                        else "FAIL"
                    ),
                }
            )
    return comparisons


def main() -> None:
    comparisons = compare_expected_cases()
    print("case_id\texpected\tobserved\tresult")
    for row in comparisons:
        print(
            f"{row['case_id']}\t{row['expected']}\t"
            f"{row['observed']}\t{row['pass']}"
        )
    failed = [row for row in comparisons if row["pass"] == "FAIL"]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

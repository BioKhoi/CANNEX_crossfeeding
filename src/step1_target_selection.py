#!/usr/bin/env python3
"""Validate literature-guided, user-selected microbial metabolite targets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from sbml_structural import load_model
from workbook_writer import write_workbook


REQUIRED_COLUMNS = {
    "target_name",
    "base_id",
    "host_relevance",
    "metabolite_class",
    "microbial_evidence",
    "selection_rationale",
    "reference",
}
FORBIDDEN_DISCOVERY_COLUMNS = {
    "expected_donor_model_id",
    "expected_precursor_id",
    "expected_recipient_model_id",
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an a priori list of literature-selected, host-relevant "
            "microbial metabolites before GEM screening."
        )
    )
    parser.add_argument("--gem-dir", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--xlsx-output", type=Path)
    return parser.parse_args()


def read_targets(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - fieldnames)
        if missing:
            raise ValueError(
                "Target file is missing required column(s): " + ", ".join(missing)
            )
        leaked = sorted(FORBIDDEN_DISCOVERY_COLUMNS & fieldnames)
        if leaked:
            raise ValueError(
                "Target discovery file contains validation-only expected-answer "
                "column(s): "
                + ", ".join(leaked)
                + ". Keep expected donor, precursor, and recipient values in "
                "the relevant validation case's config/expected_result.tsv or "
                "config/expected_contrasts.tsv file only."
            )
        rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    if not rows:
        raise ValueError("Target file contains no selected metabolites.")

    seen_names: set[str] = set()
    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        empty = sorted(column for column in REQUIRED_COLUMNS if not row[column])
        if empty:
            raise ValueError(
                f"Target row {row_number} has empty required field(s): "
                + ", ".join(empty)
            )
        normalized_name = row["target_name"].casefold()
        normalized_id = row["base_id"].casefold()
        if normalized_name in seen_names:
            raise ValueError(f"Duplicate target_name in row {row_number}: {row['target_name']}")
        if normalized_id in seen_ids:
            raise ValueError(f"Duplicate base_id in row {row_number}: {row['base_id']}")
        seen_names.add(normalized_name)
        seen_ids.add(normalized_id)
    return rows


def validate_targets(
    gem_directory: Path,
    target_file: Path,
) -> dict[str, object]:
    gem_files = sorted(gem_directory.glob("*.xml"))
    if not gem_files:
        raise FileNotFoundError(f"No XML GEM files found in: {gem_directory}")
    targets = read_targets(target_file)
    models = [load_model(path) for path in gem_files]

    rows: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    for target in targets:
        matching_models: list[str] = []
        matched_compartments: set[str] = set()
        for model in models:
            matches = [
                species
                for species in model.species.values()
                if species.base_id == target["base_id"]
            ]
            if not matches:
                continue
            matching_models.append(model.model_id)
            matched_compartments.update(record.compartment for record in matches)
            evidence.append(
                {
                    "target_name": target["target_name"],
                    "base_id": target["base_id"],
                    "model_file": model.path.name,
                    "model_id": model.model_id,
                    "bacterium": model.model_name,
                    "species_ids": "; ".join(sorted(record.species_id for record in matches)),
                    "compartments": "; ".join(sorted({record.compartment for record in matches})),
                }
            )
        represented = bool(matching_models)
        rows.append(
            {
                **target,
                "models_with_identifier": len(matching_models),
                "model_ids": "; ".join(sorted(matching_models)),
                "compartments": "; ".join(sorted(matched_compartments)),
                "decision": "Keep" if represented else "Unresolved",
                "reason": (
                    "User-selected target identifier is represented in at least one supplied GEM."
                    if represented
                    else "User-selected target identifier was not found in the supplied GEMs."
                ),
            }
        )

    kept = [row for row in rows if row["decision"] == "Keep"]
    unresolved = [row for row in rows if row["decision"] == "Unresolved"]
    return {
        "metadata": {
            "analysis": "Step 1 literature-guided user target selection",
            "selection_rule": (
                "Targets are selected a priori by the user from literature linking "
                "microbial metabolites to the host question; the pipeline does not "
                "screen all metabolites or use GEM results to select targets."
            ),
            "target_file": target_file.name,
            "gem_directory": gem_directory.name,
        },
        "summary": {
            "input_gems": len(models),
            "user_selected_targets": len(rows),
            "targets_with_gem_identifier": len(kept),
            "unresolved_targets": len(unresolved),
        },
        "rows": rows,
        "evidence": evidence,
    }


def main() -> None:
    args = parse_arguments()
    gem_directory = args.gem_dir.expanduser().resolve()
    target_file = args.targets.expanduser().resolve()
    result = validate_targets(gem_directory, target_file)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.xlsx_output:
        write_workbook(result, args.xlsx_output, "step1")
    summary = result["summary"]
    print(f"user_selected_targets\t{summary['user_selected_targets']}")
    print(f"targets_with_gem_identifier\t{summary['targets_with_gem_identifier']}")
    print(f"unresolved_targets\t{summary['unresolved_targets']}")
    print(f"json\t{args.json_output}")
    if args.xlsx_output:
        print(f"xlsx\t{args.xlsx_output}")


if __name__ == "__main__":
    main()

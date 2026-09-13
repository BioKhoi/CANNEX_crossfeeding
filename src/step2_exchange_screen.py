from __future__ import annotations

import argparse
import json
from pathlib import Path

from sbml_structural import capability_label, exchange_records, load_model
from workbook_writer import write_workbook


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gem-dir", type=Path, required=True)
    parser.add_argument("--step1-json", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--xlsx-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    gem_files = sorted(args.gem_dir.expanduser().resolve().glob("*.xml"))
    if not gem_files:
        raise FileNotFoundError(f"No XML GEMs found in {args.gem_dir}")
    step1_path = args.step1_json.expanduser().resolve()
    step1 = json.loads(step1_path.read_text(encoding="utf-8"))
    targets = [row for row in step1["rows"] if row["decision"] == "Keep"]
    if not targets:
        raise ValueError("Step 1 retained no user-selected targets with resolved GEM identifiers.")
    rows: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    for gem_file in gem_files:
        model = load_model(gem_file)
        for target in targets:
            target_evidence = exchange_records(model, target["base_id"])
            export_allowed = any(bool(record["export_allowed"]) for record in target_evidence)
            import_allowed = any(bool(record["import_allowed"]) for record in target_evidence)
            decision = "Keep" if export_allowed else "Exclude"
            if export_allowed:
                reason = "At least one target exchange permits outward release."
            elif target_evidence:
                reason = "Target exchange exists but does not permit outward release."
            else:
                reason = "No target exchange reaction was found."
            rows.append(
                {
                    "model_file": gem_file.name,
                    "model_path": str(gem_file.resolve()),
                    "model_id": model.model_id,
                    "bacterium": model.model_name,
                    "target_name": target["target_name"],
                    "target_id": target["base_id"],
                    "host_relevance": target["host_relevance"],
                    "metabolite_class": target["metabolite_class"],
                    "microbial_evidence": target["microbial_evidence"],
                    "selection_rationale": target["selection_rationale"],
                    "reference": target["reference"],
                    "exchange_present": bool(target_evidence),
                    "exchange_reactions": "; ".join(
                        str(record["reaction_id"]) for record in target_evidence
                    ),
                    "export_allowed": export_allowed,
                    "import_allowed": import_allowed,
                    "exchange_capability": (
                        capability_label(export_allowed, import_allowed)
                        if target_evidence
                        else "No exchange"
                    ),
                    "decision": decision,
                    "reason": reason,
                }
            )
            for record in target_evidence:
                evidence.append(
                    {
                        "model_file": gem_file.name,
                        "model_id": model.model_id,
                        "bacterium": model.model_name,
                        "target_name": target["target_name"],
                        "target_id": target["base_id"],
                        **record,
                        "exchange_capability": capability_label(
                            bool(record["export_allowed"]),
                            bool(record["import_allowed"]),
                        ),
                    }
                )
    kept_rows = [row for row in rows if row["decision"] == "Keep"]
    result = {
        "metadata": {
            "analysis": "Step 2 target exchange-export screen",
            "method": "SBML exchange presence and encoded direction; no flux optimization",
            "gem_directory": str(args.gem_dir.expanduser().resolve()),
            "step1_input": str(step1_path),
            "target_selection_rule": step1.get("metadata", {}).get("selection_rule", ""),
        },
        "summary": {
            "models": len(gem_files),
            "targets": len(targets),
            "model_target_tests": len(rows),
            "kept": len(kept_rows),
            "excluded": len(rows) - len(kept_rows),
            "models_with_at_least_one_candidate": len({row["model_id"] for row in kept_rows}),
        },
        "rows": rows,
        "evidence": evidence,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.xlsx_output:
        write_workbook(result, args.xlsx_output, "step2")
    print(f"models\t{len(gem_files)}")
    print(f"targets\t{len(targets)}")
    print(f"model_target_tests\t{len(rows)}")
    print(f"kept\t{len(kept_rows)}")
    print(f"excluded\t{len(rows) - len(kept_rows)}")
    print(f"json\t{args.json_output}")
    if args.xlsx_output:
        print(f"xlsx\t{args.xlsx_output}")


if __name__ == "__main__":
    main()

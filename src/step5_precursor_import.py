from __future__ import annotations

import argparse
import json
from pathlib import Path

from sbml_structural import exchange_records, load_model, transport_records
from workbook_writer import write_workbook


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step4-json", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--xlsx-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    step4_path = args.step4_json.expanduser().resolve()
    step4 = json.loads(step4_path.read_text(encoding="utf-8"))
    candidates = [row for row in step4["rows"] if row["decision"] == "Keep"]
    model_cache = {}
    rows: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    for candidate in candidates:
        model_path = candidate["model_path"]
        if model_path not in model_cache:
            model_cache[model_path] = load_model(model_path)
        model = model_cache[model_path]
        precursors = candidate.get("precursor_candidates", [])
        if not precursors:
            rows.append(
                {
                    "model_file": candidate["model_file"],
                    "model_path": model_path,
                    "model_id": candidate["model_id"],
                    "bacterium": candidate["bacterium"],
                    "target_name": candidate["target_name"],
                    "target_id": candidate["target_id"],
                    "host_relevance": candidate["host_relevance"],
                    "metabolite_class": candidate["metabolite_class"],
                    "microbial_evidence": candidate["microbial_evidence"],
                    "selection_rationale": candidate["selection_rationale"],
                    "reference": candidate["reference"],
                    "precursor_selection_mode": "",
                    "precursor_name": "",
                    "precursor_id": "",
                    "precursor_species_id": "",
                    "path_ids": "",
                    "path_count": 0,
                    "exchange_reactions": "",
                    "import_allowed": False,
                    "transport_reactions": "",
                    "inward_transport_allowed": False,
                    "decision": "Exclude",
                    "reason": "Step 4 did not nominate a non-currency environmental precursor.",
                }
            )
            continue
        for precursor in precursors:
            precursor_id = str(precursor["base_id"])
            exchange_evidence = exchange_records(model, precursor_id)
            transport_evidence = transport_records(model, precursor_id)
            import_allowed = any(bool(record["import_allowed"]) for record in exchange_evidence)
            inward_records = [
                record for record in transport_evidence if bool(record["e_to_c_allowed"])
            ]
            inward_allowed = bool(inward_records)
            decision = "Keep" if import_allowed and inward_allowed else "Exclude"
            if import_allowed and inward_allowed:
                reason = "The precursor has an import-capable exchange and an extracellular-to-cytosol transport reaction or reaction chain."
            elif not import_allowed:
                reason = "No precursor exchange permits import from the environment."
            else:
                reason = "The precursor exchange permits import, but no directionally valid extracellular-to-cytosol transport path was found."
            rows.append(
                {
                    "model_file": candidate["model_file"],
                    "model_path": model_path,
                    "model_id": candidate["model_id"],
                    "bacterium": candidate["bacterium"],
                    "target_name": candidate["target_name"],
                    "target_id": candidate["target_id"],
                    "host_relevance": candidate["host_relevance"],
                    "metabolite_class": candidate["metabolite_class"],
                    "microbial_evidence": candidate["microbial_evidence"],
                    "selection_rationale": candidate["selection_rationale"],
                    "reference": candidate["reference"],
                    "precursor_selection_mode": precursor.get(
                        "selection_mode", "automatic_minimal_path"
                    ),
                    "precursor_name": precursor["name"],
                    "precursor_id": precursor_id,
                    "precursor_species_id": precursor["species_id"],
                    "path_ids": "; ".join(
                        str(value) for value in precursor.get("path_ids", [])
                    ),
                    "path_count": len(precursor.get("path_ids", [])),
                    "exchange_reactions": "; ".join(
                        str(record["reaction_id"]) for record in exchange_evidence
                    ),
                    "import_allowed": import_allowed,
                    "transport_reactions": "; ".join(
                        str(record["reaction_id"]) for record in transport_evidence
                    ),
                    "inward_transport_allowed": inward_allowed,
                    "decision": decision,
                    "reason": reason,
                }
            )
            for record in exchange_evidence:
                evidence.append(
                    {
                        "model_file": candidate["model_file"],
                        "model_id": candidate["model_id"],
                        "bacterium": candidate["bacterium"],
                        "target_name": candidate["target_name"],
                        "target_id": candidate["target_id"],
                        "precursor_name": precursor["name"],
                        "precursor_id": precursor_id,
                        "evidence_type": "Exchange import",
                        "reaction_id": record["reaction_id"],
                        "reaction_name": record["reaction_name"],
                        "equation": record["equation"],
                        "lower_bound": record["lower_bound"],
                        "upper_bound": record["upper_bound"],
                        "required_direction_allowed": record["import_allowed"],
                    }
                )
            for record in transport_evidence:
                evidence.append(
                    {
                        "model_file": candidate["model_file"],
                        "model_id": candidate["model_id"],
                        "bacterium": candidate["bacterium"],
                        "target_name": candidate["target_name"],
                        "target_id": candidate["target_id"],
                        "precursor_name": precursor["name"],
                        "precursor_id": precursor_id,
                        "evidence_type": "Extracellular-to-cytosol transport",
                        "reaction_id": record["reaction_id"],
                        "reaction_name": record["reaction_name"],
                        "equation": record["equation"],
                        "lower_bound": record["lower_bound"],
                        "upper_bound": record["upper_bound"],
                        "required_direction_allowed": record["e_to_c_allowed"],
                    }
                )
    kept_rows = [row for row in rows if row["decision"] == "Keep"]
    kept_pairs = {
        (row["model_id"], row["target_id"])
        for row in kept_rows
    }
    result = {
        "metadata": {
            "analysis": "Step 5 precursor import screen",
            "method": "FBC exchange-import and extracellular-to-cytosol transport structure; no flux optimization",
            "precursor_definition": (
                "Automatically discovered non-currency extracellular root seed "
                "used by at least one Step 4 net-positive alternative path"
            ),
            "step4_input": str(step4_path),
        },
        "summary": {
            "step4_candidates_tested": len(candidates),
            "precursor_tests": len(rows),
            "kept": len(kept_rows),
            "excluded": len(rows) - len(kept_rows),
            "model_target_pairs_with_importable_precursor": len(kept_pairs),
        },
        "rows": rows,
        "evidence": evidence,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.xlsx_output:
        write_workbook(result, args.xlsx_output, "step5")
    print(f"step4_candidates_tested\t{len(candidates)}")
    print(f"precursor_tests\t{len(rows)}")
    print(f"kept\t{len(kept_rows)}")
    print(f"excluded\t{len(rows) - len(kept_rows)}")
    print(f"json\t{args.json_output}")
    if args.xlsx_output:
        print(f"xlsx\t{args.xlsx_output}")


if __name__ == "__main__":
    main()

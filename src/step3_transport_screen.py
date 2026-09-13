from __future__ import annotations

import argparse
import json
from pathlib import Path

from sbml_structural import load_model, target_species_ids, transport_records
from workbook_writer import write_workbook


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step2-json", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--xlsx-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    step2_path = args.step2_json.expanduser().resolve()
    step2 = json.loads(step2_path.read_text(encoding="utf-8"))
    candidates = [row for row in step2["rows"] if row["decision"] == "Keep"]
    model_cache = {}
    rows: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    for candidate in candidates:
        model_path = candidate["model_path"]
        if model_path not in model_cache:
            model_cache[model_path] = load_model(model_path)
        model = model_cache[model_path]
        target_id = str(candidate["target_id"])
        internal_ids = target_species_ids(model, target_id, "c")
        external_ids = target_species_ids(model, target_id, "e")
        target_transport = transport_records(model, target_id)
        outward = [record for record in target_transport if record["c_to_e_allowed"]]
        inward = [record for record in target_transport if record["e_to_c_allowed"]]
        outward_allowed = bool(outward)
        inward_allowed = bool(inward)
        if outward_allowed and inward_allowed:
            capability = "Cytosol and extracellular (both directions)"
        elif outward_allowed:
            capability = "Cytosol to extracellular only"
        elif inward_allowed:
            capability = "Extracellular to cytosol only"
        else:
            capability = "No target compartment connection"
        decision = "Keep" if internal_ids and external_ids and outward_allowed else "Exclude"
        if not internal_ids:
            reason = "No cytosolic target species was found."
        elif not external_ids:
            reason = "No extracellular target species was found."
        elif outward_allowed:
            reason = "At least one target transport reaction or reaction chain permits cytosol-to-extracellular movement."
        elif inward_allowed:
            reason = "Target transport exists but permits only extracellular-to-cytosol movement."
        else:
            reason = "No directionally valid reaction path connects the cytosolic and extracellular target forms."
        rows.append(
            {
                "model_file": candidate["model_file"],
                "model_path": model_path,
                "model_id": candidate["model_id"],
                "bacterium": candidate["bacterium"],
                "target_name": candidate["target_name"],
                "target_id": target_id,
                "host_relevance": candidate["host_relevance"],
                "metabolite_class": candidate["metabolite_class"],
                "microbial_evidence": candidate["microbial_evidence"],
                "selection_rationale": candidate["selection_rationale"],
                "reference": candidate["reference"],
                "step2_exchange_reactions": candidate["exchange_reactions"],
                "step2_exchange_capability": candidate["exchange_capability"],
                "internal_species_ids": "; ".join(internal_ids),
                "external_species_ids": "; ".join(external_ids),
                "transport_reactions": "; ".join(
                    str(record["reaction_id"]) for record in target_transport
                ),
                "outward_transport_count": len(outward),
                "inward_transport_count": len(inward),
                "outward_transport_allowed": outward_allowed,
                "inward_transport_allowed": inward_allowed,
                "transport_capability": capability,
                "decision": decision,
                "reason": reason,
            }
        )
        for record in target_transport:
            evidence.append(
                {
                    "model_file": candidate["model_file"],
                    "model_id": candidate["model_id"],
                    "bacterium": candidate["bacterium"],
                    "target_name": candidate["target_name"],
                    "target_id": target_id,
                    **record,
                }
            )
    kept_rows = [row for row in rows if row["decision"] == "Keep"]
    result = {
        "metadata": {
            "analysis": "Step 3 cytosol-to-extracellular target transport screen",
            "method": "SBML compartment connection and encoded reaction direction; no flux optimization",
            "step2_input": str(step2_path),
        },
        "summary": {
            "step2_candidates_tested": len(rows),
            "kept": len(kept_rows),
            "excluded": len(rows) - len(kept_rows),
            "models_with_at_least_one_transport_candidate": len(
                {row["model_id"] for row in kept_rows}
            ),
        },
        "rows": rows,
        "evidence": evidence,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.xlsx_output:
        write_workbook(result, args.xlsx_output, "step3")
    print(f"step2_candidates_tested\t{len(rows)}")
    print(f"kept\t{len(kept_rows)}")
    print(f"excluded\t{len(rows) - len(kept_rows)}")
    print(f"json\t{args.json_output}")
    if args.xlsx_output:
        print(f"xlsx\t{args.xlsx_output}")


if __name__ == "__main__":
    main()

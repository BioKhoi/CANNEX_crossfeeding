from __future__ import annotations

import argparse
import csv
import json
import tempfile
from collections import defaultdict
from pathlib import Path

from sbml_structural import (
    directional_reaction_records,
    exchange_inventory,
    exchange_records,
    load_model,
    target_species_ids,
    transport_records,
)
from step4_intracellular_production import (
    COFACTOR_BOOTSTRAP,
    menetools_version,
    parse_diet,
    pathway_steps,
    run_menetools,
    write_normalized_network,
    write_species_document,
)
from workbook_writer import write_workbook


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step5-json", type=Path, required=True)
    parser.add_argument("--gem-dir", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--diet", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--xlsx-output", type=Path)
    parser.add_argument("--mene", type=Path, required=True)
    parser.add_argument(
        "--condition-label",
        default="User-supplied diet; anaerobic (oxygen withheld)",
    )
    return parser.parse_args()


def read_model_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"model_file", "species", "strain", "sha256", "source"}
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError(
                "Model manifest is missing required column(s): " + ", ".join(missing)
            )
        rows = {
            str(row["model_file"]).strip(): {
                key: str(value or "").strip() for key, value in row.items()
            }
            for row in reader
            if str(row.get("model_file", "")).strip()
        }
    if not rows:
        raise ValueError("Model manifest contains no model records.")
    return rows


def read_linked_result(
    document: dict[str, object],
    metadata_key: str,
    document_path: Path,
) -> tuple[dict[str, object], Path]:
    metadata = document.get("metadata", {})
    linked_value = metadata.get(metadata_key) if isinstance(metadata, dict) else None
    if not linked_value:
        raise ValueError(f"Missing metadata link: {metadata_key} in {document_path}")
    linked_path = Path(str(linked_value)).expanduser()
    if not linked_path.is_absolute():
        linked_path = document_path.parent / linked_path
    linked_path = linked_path.resolve()
    if not linked_path.is_file():
        raise FileNotFoundError(
            f"Required linked evidence file was not found: {linked_path}"
        )
    return json.loads(linked_path.read_text(encoding="utf-8")), linked_path


def build_consumer_evidence(
    step5: dict[str, object],
    step5_path: Path,
    recipient_rows: list[dict[str, object]],
    edge_rows: list[dict[str, object]],
    strain_id_by_model: dict[str, int],
) -> list[dict[str, object]]:
    step4, step4_path = read_linked_result(step5, "step4_input", step5_path)
    step3, step3_path = read_linked_result(step4, "step3_input", step4_path)
    step2, _ = read_linked_result(step3, "step2_input", step3_path)

    edge_ids_by_consumer: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for edge in edge_rows:
        key = (
            str(edge["recipient_model_id"]),
            str(edge["precursor_id"]),
            str(edge["final_target_id"]),
        )
        edge_ids_by_consumer[key].append(int(edge["edge_id"]))

    consumer_evidence: list[dict[str, object]] = []

    def add_record(
        candidate: dict[str, object],
        source_step: int,
        evidence_type: str,
        record: dict[str, object],
        direction: str,
        required_direction_allowed: bool,
        forms_target_inside_cell: bool = False,
    ) -> None:
        key = (
            str(candidate["model_id"]),
            str(candidate["precursor_id"]),
            str(candidate["target_id"]),
        )
        consumer_evidence.append(
            {
                "edge_ids": "; ".join(
                    str(value) for value in edge_ids_by_consumer.get(key, [])
                ),
                "consumer_strain_id": strain_id_by_model[str(candidate["model_id"])],
                "consumer_bacterium": candidate["bacterium"],
                "precursor_name": candidate["precursor_name"],
                "precursor_id": candidate["precursor_id"],
                "target_name": candidate["target_name"],
                "target_id": candidate["target_id"],
                "source_step": source_step,
                "evidence_type": evidence_type,
                "path_step": record.get("path_step"),
                "reaction_id": record.get("reaction_id", ""),
                "reaction_name": record.get("reaction_name", ""),
                "direction": direction,
                "equation": record.get("equation", ""),
                "lower_bound": record.get("lower_bound"),
                "upper_bound": record.get("upper_bound"),
                "required_direction_allowed": required_direction_allowed,
                "forms_target_inside_cell": forms_target_inside_cell,
                "evidence_scope": record.get("evidence_scope", ""),
            }
        )

    for candidate in recipient_rows:
        model_id = str(candidate["model_id"])
        target_id = str(candidate["target_id"])
        precursor_id = str(candidate["precursor_id"])

        for record in step5.get("evidence", []):
            if (
                str(record.get("model_id")) == model_id
                and str(record.get("target_id")) == target_id
                and str(record.get("precursor_id")) == precursor_id
            ):
                is_exchange = str(record.get("evidence_type")) == "Exchange import"
                add_record(
                    candidate,
                    5,
                    "Precursor exchange import" if is_exchange else "Precursor inward transport",
                    record,
                    "environment to extracellular" if is_exchange else "extracellular to cytosol",
                    bool(record.get("required_direction_allowed")),
                )

        for record in step4.get("evidence", []):
            if (
                str(record.get("model_id")) == model_id
                and str(record.get("target_id")) == target_id
            ):
                add_record(
                    candidate,
                    4,
                    "Target production pathway",
                    record,
                    str(record.get("direction", "")),
                    True,
                    bool(record.get("forms_target_inside_cell")),
                )

        for record in step3.get("evidence", []):
            if (
                str(record.get("model_id")) == model_id
                and str(record.get("target_id")) == target_id
            ):
                add_record(
                    candidate,
                    3,
                    "Target outward transport",
                    record,
                    "cytosol to extracellular",
                    bool(record.get("c_to_e_allowed")),
                )

        for record in step2.get("evidence", []):
            if (
                str(record.get("model_id")) == model_id
                and str(record.get("target_id")) == target_id
            ):
                add_record(
                    candidate,
                    2,
                    "Target exchange export",
                    record,
                    "extracellular to environment",
                    bool(record.get("export_allowed")),
                )

    return sorted(
        consumer_evidence,
        key=lambda value: (
            int(value["consumer_strain_id"]),
            str(value["target_name"]),
            int(value["source_step"]),
            int(value["path_step"]) if value["path_step"] is not None else 999,
            str(value["reaction_id"]),
        ),
    )


def production_audit(
    model,
    donor_species: str,
    precursor_id: str,
    precursor_name: str,
    diet_bases: set[str],
    mene_path: Path,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    cytosolic_ids = target_species_ids(model, precursor_id, "c")
    extracellular_ids = target_species_ids(model, precursor_id, "e")
    exchanges = exchange_records(model, precursor_id)
    transports = transport_records(model, precursor_id)
    export_exchanges = [record for record in exchanges if bool(record["export_allowed"])]
    outward_transports = [record for record in transports if bool(record["c_to_e_allowed"])]
    target_species_id = cytosolic_ids[0] if cytosolic_ids else ""
    evidence: list[dict[str, object]] = []
    for record in exchanges:
        evidence.append(
            {
                "donor_model_file": model.path.name,
                "donor_model_id": model.model_id,
                "donor_bacterium": model.model_name,
                "donor_species": donor_species,
                "precursor_name": precursor_name,
                "precursor_id": precursor_id,
                "evidence_type": "Exchange export",
                "path_step": None,
                "reaction_id": record["reaction_id"],
                "reaction_name": record["reaction_name"],
                "direction": "external to environment",
                "equation": record["equation"],
                "lower_bound": record["lower_bound"],
                "upper_bound": record["upper_bound"],
                "required_direction_allowed": bool(record["export_allowed"]),
                "forms_precursor_inside_cell": False,
            }
        )
    for record in transports:
        evidence.append(
            {
                "donor_model_file": model.path.name,
                "donor_model_id": model.model_id,
                "donor_bacterium": model.model_name,
                "donor_species": donor_species,
                "precursor_name": precursor_name,
                "precursor_id": precursor_id,
                "evidence_type": "Outward transport",
                "path_step": None,
                "reaction_id": record["reaction_id"],
                "reaction_name": record["reaction_name"],
                "direction": "cytosol to extracellular",
                "equation": record["equation"],
                "lower_bound": record["lower_bound"],
                "upper_bound": record["upper_bound"],
                "required_direction_allowed": bool(record["c_to_e_allowed"]),
                "forms_precursor_inside_cell": False,
            }
        )
    target_scope_reachable = False
    internally_producible = False
    menetools_compatibility_fallback = False
    target_reactions: list[dict[str, object]] = []
    selected_records: list[dict[str, object]] = []
    environmental_seed_ids: set[str] = set()
    cofactor_seed_ids: set[str] = set()
    if target_species_id:
        exchange_inventory_records = exchange_inventory(model)
        importable_bases = {
            str(record["base_id"])
            for record in exchange_inventory_records
            if bool(record["import_allowed"])
        }
        external_by_base = {
            record.base_id: species_id
            for species_id, record in model.species.items()
            if record.compartment == "e"
        }
        cytosolic_by_base = {
            record.base_id: species_id
            for species_id, record in model.species.items()
            if record.compartment == "c"
        }
        seed_bases = (
            diet_bases & importable_bases & set(external_by_base)
        ) - {precursor_id, "o2"}
        environmental_seed_ids = {external_by_base[base] for base in seed_bases}
        cofactor_seed_ids = {
            cytosolic_by_base[base]
            for base in COFACTOR_BOOTSTRAP
            if base != precursor_id and base in cytosolic_by_base
        }
        seed_ids = environmental_seed_ids | cofactor_seed_ids
        directed_records = directional_reaction_records(model)
        record_by_id = {
            str(record["normalized_id"]): record for record in directed_records
        }
        with tempfile.TemporaryDirectory(prefix="crossfeeding_step6_") as temporary_directory:
            temporary = Path(temporary_directory)
            network_path = temporary / "network.xml"
            seed_path = temporary / "seeds.xml"
            target_path = temporary / "target.xml"
            mene_output = temporary / "mene_path.json"
            write_normalized_network(network_path, model, directed_records)
            write_species_document(seed_path, model, seed_ids, "step6_seeds")
            write_species_document(target_path, model, {target_species_id}, "step6_target")
            mene_result = run_menetools(
                mene_path,
                network_path,
                seed_path,
                target_path,
                mene_output,
            )
        unproducible = set(mene_result.get("unproducible_targets_lst", []))
        menetools_compatibility_fallback = bool(
            mene_result.get("menetools_compatibility_fallback", False)
        )
        selected_ids = [str(value) for value in mene_result.get("one_path", [])]
        selected_records = [
            record_by_id[value] for value in selected_ids if value in record_by_id
        ]
        for record in selected_records:
            product_ids = {species_id for species_id, _ in record["products"]}
            substrate_bases = {
                model.species[species_id].base_id
                for species_id, _ in record["reactants"]
                if species_id in model.species
            }
            if target_species_id in product_ids and precursor_id not in substrate_bases:
                target_reactions.append(record)
        target_scope_reachable = target_species_id not in unproducible
        internally_producible = target_scope_reachable and bool(target_reactions)
        steps = pathway_steps(selected_records, seed_ids)
        target_normalized_ids = {
            str(record["normalized_id"]) for record in target_reactions
        }
        for record in sorted(
            selected_records,
            key=lambda value: (
                steps.get(str(value["normalized_id"]), 999),
                str(value["reaction_id"]),
            ),
        ):
            normalized_id = str(record["normalized_id"])
            evidence.append(
                {
                    "donor_model_file": model.path.name,
                    "donor_model_id": model.model_id,
                    "donor_bacterium": model.model_name,
                    "donor_species": donor_species,
                    "precursor_name": precursor_name,
                    "precursor_id": precursor_id,
                    "evidence_type": "Donor pathway",
                    "path_step": steps.get(normalized_id),
                    "reaction_id": record["reaction_id"],
                    "reaction_name": record["reaction_name"],
                    "direction": record["direction"],
                    "equation": record["equation"],
                    "lower_bound": None,
                    "upper_bound": None,
                    "required_direction_allowed": True,
                    "forms_precursor_inside_cell": normalized_id in target_normalized_ids,
                }
            )
    donor_pass = internally_producible and bool(outward_transports) and bool(export_exchanges)
    if donor_pass:
        reason = "The different-species donor can form the precursor intracellularly, transport it outward through a reaction or reaction chain, and export it through an exchange reaction."
    elif not cytosolic_ids:
        reason = "The donor GEM lacks a cytosolic form of the precursor."
    elif not internally_producible:
        reason = "No target-withheld intracellular production path was retained for the precursor."
    elif not outward_transports:
        reason = "The donor GEM lacks a directionally valid precursor transport path from cytosol to extracellular space."
    else:
        reason = "The donor GEM lacks an export-capable precursor exchange reaction."
    audit = {
        "donor_model_file": model.path.name,
        "donor_model_path": str(model.path),
        "donor_model_id": model.model_id,
        "donor_bacterium": model.model_name,
        "donor_species": donor_species,
        "precursor_name": precursor_name,
        "precursor_id": precursor_id,
        "cytosolic_species_ids": "; ".join(cytosolic_ids),
        "extracellular_species_ids": "; ".join(extracellular_ids),
        "environmental_seed_count": len(environmental_seed_ids),
        "cofactor_bootstrap_count": len(cofactor_seed_ids),
        "precursor_withheld": True,
        "mene_target_reachable": target_scope_reachable,
        "internal_production": internally_producible,
        "production_reactions": "; ".join(
            f"{record['reaction_id']} [{record['direction']}]" for record in target_reactions
        ),
        "minimal_path_reaction_count": len(selected_records),
        "menetools_compatibility_fallback": menetools_compatibility_fallback,
        "minimal_path_reactions": "; ".join(
            f"{record['reaction_id']} [{record['direction']}]" for record in selected_records
        ),
        "outward_transport": bool(outward_transports),
        "transport_reactions": "; ".join(
            str(record["reaction_id"]) for record in outward_transports
        ),
        "exchange_export": bool(export_exchanges),
        "exchange_reactions": "; ".join(
            str(record["reaction_id"]) for record in export_exchanges
        ),
        "donor_pass": donor_pass,
        "decision": "Keep" if donor_pass else "Exclude",
        "reason": reason,
    }
    return audit, evidence


def main() -> None:
    args = parse_arguments()
    step5_path = args.step5_json.expanduser().resolve()
    gem_directory = args.gem_dir.expanduser().resolve()
    manifest_path = args.model_manifest.expanduser().resolve()
    diet_path = args.diet.expanduser().resolve()
    mene_path = args.mene.expanduser().resolve()
    step5 = json.loads(step5_path.read_text(encoding="utf-8"))
    recipient_rows = [row for row in step5["rows"] if row["decision"] == "Keep"]
    models = [load_model(path) for path in sorted(gem_directory.glob("*.xml"))]
    manifest = read_model_manifest(manifest_path)
    missing_manifest = sorted(model.path.name for model in models if model.path.name not in manifest)
    if missing_manifest:
        raise ValueError(
            "Model manifest lacks supplied GEM file(s): " + ", ".join(missing_manifest)
        )
    strain_id_by_model = {
        model.model_id: index for index, model in enumerate(models, start=1)
    }
    strain_key = [
        {
            "strain_id": strain_id_by_model[model.model_id],
            "bacterium": model.model_name,
            "gem_file": model.path.name,
            "species": manifest[model.path.name]["species"],
            "strain": manifest[model.path.name]["strain"],
            "sha256": manifest[model.path.name]["sha256"],
        }
        for model in models
    ]
    diet_bases = parse_diet(diet_path)
    requested_audits: dict[tuple[str, str], dict[str, object]] = {}
    same_species_not_tested = 0
    for recipient in recipient_rows:
        recipient_species = manifest[str(recipient["model_file"])]["species"]
        for model in models:
            donor_species = manifest[model.path.name]["species"]
            if donor_species.lower() == recipient_species.lower():
                same_species_not_tested += 1
                continue
            key = (str(model.path), str(recipient["precursor_id"]))
            requested_audits[key] = {
                "model": model,
                "precursor_id": str(recipient["precursor_id"]),
                "precursor_name": str(recipient["precursor_name"]),
            }
    audits: dict[tuple[str, str], dict[str, object]] = {}
    evidence: list[dict[str, object]] = []
    for key, request in sorted(requested_audits.items()):
        audit, audit_evidence = production_audit(
            request["model"],
            manifest[request["model"].path.name]["species"],
            str(request["precursor_id"]),
            str(request["precursor_name"]),
            diet_bases,
            mene_path,
        )
        audit["donor_strain_id"] = strain_id_by_model[str(audit["donor_model_id"])]
        audits[key] = audit
        evidence.extend(audit_evidence)
    rows: list[dict[str, object]] = []
    for recipient in recipient_rows:
        recipient_species = manifest[str(recipient["model_file"])]["species"]
        for model in models:
            donor_species = manifest[model.path.name]["species"]
            if donor_species.lower() == recipient_species.lower():
                continue
            audit = audits[(str(model.path), str(recipient["precursor_id"]))]
            rows.append(
                {
                    "edge_id": len(rows) + 1,
                    "donor_strain_id": strain_id_by_model[str(audit["donor_model_id"])],
                    "donor_model_file": audit["donor_model_file"],
                    "donor_model_path": audit["donor_model_path"],
                    "donor_model_id": audit["donor_model_id"],
                    "donor_bacterium": audit["donor_bacterium"],
                    "donor_species": audit["donor_species"],
                    "precursor_name": audit["precursor_name"],
                    "precursor_id": audit["precursor_id"],
                    "recipient_path_ids": recipient.get("path_ids", ""),
                    "recipient_path_count": recipient.get("path_count", 0),
                    "recipient_model_file": recipient["model_file"],
                    "recipient_model_path": recipient["model_path"],
                    "recipient_model_id": recipient["model_id"],
                    "recipient_strain_id": strain_id_by_model[str(recipient["model_id"])],
                    "recipient_bacterium": recipient["bacterium"],
                    "recipient_species": recipient_species,
                    "target_export_pass": True,
                    "target_production_pass": True,
                    "precursor_import_pass": bool(
                        recipient["import_allowed"]
                        and recipient["inward_transport_allowed"]
                    ),
                    "final_target": recipient["target_name"],
                    "final_target_id": recipient["target_id"],
                    "host_relevance": recipient["host_relevance"],
                    "metabolite_class": recipient["metabolite_class"],
                    "microbial_evidence": recipient["microbial_evidence"],
                    "selection_rationale": recipient["selection_rationale"],
                    "target_reference": recipient["reference"],
                    "precursor_selection_mode": recipient.get(
                        "precursor_selection_mode",
                        "automatic_bounded_alternative_paths",
                    ),
                    "species_different": True,
                    "internal_production": audit["internal_production"],
                    "production_reactions": audit["production_reactions"],
                    "outward_transport": audit["outward_transport"],
                    "transport_reactions": audit["transport_reactions"],
                    "exchange_export": audit["exchange_export"],
                    "exchange_reactions": audit["exchange_reactions"],
                    "decision": audit["decision"],
                    "reason": audit["reason"],
                }
            )
    donor_edge_context: dict[tuple[str, str], dict[str, set[object]]] = defaultdict(
        lambda: {
            "edge_ids": set(),
            "recipient_strain_ids": set(),
            "target_producers": set(),
            "final_targets": set(),
        }
    )
    for row in rows:
        key = (str(row["donor_model_id"]), str(row["precursor_id"]))
        donor_edge_context[key]["edge_ids"].add(int(row["edge_id"]))
        donor_edge_context[key]["recipient_strain_ids"].add(
            int(row["recipient_strain_id"])
        )
        donor_edge_context[key]["target_producers"].add(
            str(row["recipient_bacterium"])
        )
        donor_edge_context[key]["final_targets"].add(str(row["final_target"]))
    for record in evidence:
        donor_model_id = str(record["donor_model_id"])
        key = (donor_model_id, str(record["precursor_id"]))
        context = donor_edge_context.get(key, {})
        record["donor_strain_id"] = strain_id_by_model[donor_model_id]
        record["edge_ids"] = "; ".join(
            str(value) for value in sorted(context.get("edge_ids", set()))
        )
        record["recipient_strain_ids"] = "; ".join(
            str(value)
            for value in sorted(context.get("recipient_strain_ids", set()))
        )
        record["target_producers"] = "; ".join(
            str(value) for value in sorted(context.get("target_producers", set()))
        )
        record["final_targets"] = "; ".join(
            str(value) for value in sorted(context.get("final_targets", set()))
        )
    consumer_evidence = build_consumer_evidence(
        step5,
        step5_path,
        recipient_rows,
        rows,
        strain_id_by_model,
    )
    kept_rows = [row for row in rows if row["decision"] == "Keep"]
    kept_audits = [audit for audit in audits.values() if audit["decision"] == "Keep"]
    result = {
        "metadata": {
            "analysis": "Step 6 cross-species precursor donor screen",
            "method": "Target-withheld MeneTools intracellular production plus FBC outward transport and exchange export; no flux optimization",
            "eligibility_rule": "Donor species from the model manifest must differ from recipient species; same species/different strain is not tested",
            "donor_pass_rule": "Internal production AND cytosol-to-extracellular transport AND exchange export",
            "interpretation": "Retained rows are potential cross-species precursor-supply edges, not confirmed cross-feeding",
            "condition": args.condition_label,
            "step5_input": str(step5_path),
            "gem_directory": str(gem_directory),
            "model_manifest": str(manifest_path),
            "diet_file": str(diet_path),
            "menetools_version": menetools_version(mene_path),
            "strain_id_rule": "Numeric IDs 1..N are assigned by sorted GEM filename for each run",
        },
        "summary": {
            "input_gems": len(models),
            "step5_recipient_precursor_rows": len(recipient_rows),
            "all_recipient_donor_model_pairs": len(recipient_rows) * len(models),
            "same_species_pairs_not_tested": same_species_not_tested,
            "eligible_cross_species_edge_tests": len(rows),
            "unique_donor_precursor_audits": len(audits),
            "donor_precursor_audits_kept": len(kept_audits),
            "potential_edges_kept": len(kept_rows),
            "eligible_edges_excluded": len(rows) - len(kept_rows),
            "consumer_evidence_rows": len(consumer_evidence),
            "target_formation_evidence_rows": sum(
                bool(record["forms_target_inside_cell"])
                for record in consumer_evidence
            ),
        },
        "strain_key": strain_key,
        "rows": rows,
        "donor_audits": list(audits.values()),
        "evidence": evidence,
        "consumer_evidence": consumer_evidence,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.xlsx_output:
        write_workbook(result, args.xlsx_output, "step6")
    print(f"input_gems\t{len(models)}")
    print(f"step5_recipient_precursor_rows\t{len(recipient_rows)}")
    print(f"same_species_pairs_not_tested\t{same_species_not_tested}")
    print(f"eligible_cross_species_edge_tests\t{len(rows)}")
    print(f"unique_donor_precursor_audits\t{len(audits)}")
    print(f"potential_edges_kept\t{len(kept_rows)}")
    print(f"json\t{args.json_output}")
    if args.xlsx_output:
        print(f"xlsx\t{args.xlsx_output}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from sbml_structural import directional_reaction_records, exchange_inventory, load_model
from workbook_writer import write_workbook
COFACTOR_BOOTSTRAP = {
    "amp",
    "adp",
    "atp",
    "coa",
    "fad",
    "h",
    "h2o",
    "nad",
    "nadp",
    "pi",
    "ppi",
}
CURRENCY_METABOLITES = COFACTOR_BOOTSTRAP | {
    "fadh2",
    "nadh",
    "nadph",
}
NON_CANDIDATE_PRECURSORS = CURRENCY_METABOLITES | {
    "ca2",
    "cl",
    "cobalt2",
    "cu2",
    "fe2",
    "fe3",
    "k",
    "mg2",
    "mn2",
    "na1",
    "zn2",
}
MAX_ALTERNATIVE_PATHS = 25
MAX_PATH_SOLVER_CALLS = 200
SBML_NAMESPACE = "http://www.sbml.org/sbml/level3/version1/core"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step3-json", type=Path, required=True)
    parser.add_argument("--diet", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--xlsx-output", type=Path)
    parser.add_argument("--mene", type=Path, required=True)
    parser.add_argument(
        "--condition-label",
        default="User-supplied diet; anaerobic (oxygen withheld)",
    )
    return parser.parse_args()


def parse_diet(path: Path) -> set[str]:
    bases: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            fields = line.split()
            if len(fields) < 2:
                continue
            reaction_id, value_text = fields[:2]
            if not reaction_id.startswith("EX_") or not reaction_id.endswith("(e)"):
                continue
            try:
                value = float(value_text)
            except ValueError:
                continue
            if value < 0:
                bases.add(reaction_id[3:-3])
    bases.discard("o2")
    return bases


def sbml_tag(name: str) -> str:
    return f"{{{SBML_NAMESPACE}}}{name}"


def write_species_document(path: Path, model, species_ids: set[str], model_id: str) -> None:
    root = ET.Element(sbml_tag("sbml"), {"level": "3", "version": "1"})
    document_model = ET.SubElement(root, sbml_tag("model"), {"id": model_id})
    compartments = sorted(
        {model.species[species_id].compartment or "c" for species_id in species_ids}
    )
    compartment_list = ET.SubElement(document_model, sbml_tag("listOfCompartments"))
    for compartment in compartments:
        ET.SubElement(
            compartment_list,
            sbml_tag("compartment"),
            {"id": compartment, "constant": "true"},
        )
    species_list = ET.SubElement(document_model, sbml_tag("listOfSpecies"))
    for species_id in sorted(species_ids):
        record = model.species[species_id]
        ET.SubElement(
            species_list,
            sbml_tag("species"),
            {
                "id": species_id,
                "name": record.name,
                "compartment": record.compartment or "c",
                "boundaryCondition": "false",
                "constant": "false",
                "hasOnlySubstanceUnits": "false",
            },
        )
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def write_normalized_network(path: Path, model, directed_records: list[dict[str, object]]) -> None:
    root = ET.Element(sbml_tag("sbml"), {"level": "3", "version": "1"})
    document_model = ET.SubElement(root, sbml_tag("model"), {"id": f"{model.model_id}_fbc_normalized"})
    compartments = sorted({record.compartment or "c" for record in model.species.values()})
    compartment_list = ET.SubElement(document_model, sbml_tag("listOfCompartments"))
    for compartment in compartments:
        ET.SubElement(
            compartment_list,
            sbml_tag("compartment"),
            {"id": compartment, "constant": "true"},
        )
    species_list = ET.SubElement(document_model, sbml_tag("listOfSpecies"))
    for species_id, record in sorted(model.species.items()):
        ET.SubElement(
            species_list,
            sbml_tag("species"),
            {
                "id": species_id,
                "name": record.name,
                "compartment": record.compartment or "c",
                "boundaryCondition": "false",
                "constant": "false",
                "hasOnlySubstanceUnits": "false",
            },
        )
    reaction_list = ET.SubElement(document_model, sbml_tag("listOfReactions"))
    for record in directed_records:
        reaction = ET.SubElement(
            reaction_list,
            sbml_tag("reaction"),
            {
                "id": str(record["normalized_id"]),
                "name": str(record["reaction_name"]),
                "reversible": "false",
                "fast": "false",
            },
        )
        reactant_list = ET.SubElement(reaction, sbml_tag("listOfReactants"))
        for species_id, coefficient in record["reactants"]:
            ET.SubElement(
                reactant_list,
                sbml_tag("speciesReference"),
                {"species": species_id, "stoichiometry": f"{coefficient:g}", "constant": "true"},
            )
        product_list = ET.SubElement(reaction, sbml_tag("listOfProducts"))
        for species_id, coefficient in record["products"]:
            ET.SubElement(
                product_list,
                sbml_tag("speciesReference"),
                {"species": species_id, "stoichiometry": f"{coefficient:g}", "constant": "true"},
            )
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def run_menetools(
    mene_path: Path,
    network_path: Path,
    seed_path: Path,
    target_path: Path,
    output_path: Path,
) -> dict[str, object]:
    if not mene_path.is_file():
        raise FileNotFoundError(f"MeneTools executable was not found: {mene_path}")
    environment = executable_environment(mene_path)
    completed = subprocess.run(
        [
            str(mene_path),
            "path",
            "-d",
            str(network_path),
            "-s",
            str(seed_path),
            "-t",
            str(target_path),
            "--min",
            "--output",
            str(output_path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=environment,
        timeout=300,
    )
    if (
        completed.returncode != 0
        and "unproducible targets" in completed.stdout
        and "UnboundLocalError" in completed.stdout
    ):
        target_root = ET.parse(target_path).getroot()
        target_ids = sorted(
            element.attrib["id"]
            for element in target_root.iter()
            if element.tag == sbml_tag("species") and element.attrib.get("id")
        )
        # MeneTools 3.4.0 raises an internal one_path error when its single
        # requested target is unproducible.  Preserve that scientific null
        # result instead of converting it into a pipeline failure.
        if len(target_ids) == 1:
            return {
                "unproducible_targets_lst": target_ids,
                "one_path": [],
                "union_path": [],
                "intersection_path": [],
                "menetools_compatibility_fallback": True,
            }
    if completed.returncode != 0 or not output_path.is_file():
        raise RuntimeError(
            f"MeneTools failed with exit code {completed.returncode}:\n{completed.stdout[-4000:]}"
        )
    return json.loads(output_path.read_text(encoding="utf-8"))


def menetools_version(mene_path: Path) -> str:
    environment = executable_environment(mene_path)
    completed = subprocess.run(
        [str(mene_path), "--version"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
        env=environment,
    )
    output = completed.stdout.strip()
    match = re.search(r"\bmene\s+\d+(?:\.\d+)+", output, flags=re.IGNORECASE)
    return match.group(0) if completed.returncode == 0 and match else "unknown"


def executable_environment(executable_path: Path) -> dict[str, str]:
    """Return an environment with an executable directory first on PATH."""
    environment = os.environ.copy()
    existing_path = environment.get("PATH", "")
    path_parts = [str(executable_path.parent)]
    if existing_path:
        path_parts.append(existing_path)
    environment["PATH"] = os.pathsep.join(path_parts)
    return environment


def pathway_steps(selected: list[dict[str, object]], seeds: set[str]) -> dict[str, int]:
    available = set(seeds)
    remaining = {str(record["normalized_id"]): record for record in selected}
    steps: dict[str, int] = {}
    step = 1
    while remaining:
        activated = [
            reaction_id
            for reaction_id, record in remaining.items()
            if {species_id for species_id, _ in record["reactants"]} <= available
        ]
        if not activated:
            for reaction_id in remaining:
                steps[reaction_id] = step
            break
        for reaction_id in activated:
            record = remaining.pop(reaction_id)
            steps[reaction_id] = step
            available.update(species_id for species_id, _ in record["products"])
        step += 1
    return steps


def target_forming_reactions(
    selected_records: list[dict[str, object]],
    target_species_id: str,
) -> list[dict[str, object]]:
    return [
        record
        for record in selected_records
        if target_species_id
        in {species_id for species_id, _ in record["products"]}
    ]


def net_production_feasibility(
    selected_records: list[dict[str, object]],
    seed_ids: set[str],
    target_species_id: str,
) -> dict[str, object]:
    """Require a directionally fixed path to support positive net target formation.

    MeneTools paths are qualitative reaction sets.  This second-stage check
    assigns non-negative reaction weights, permits supplied seeds to be
    consumed, prevents non-seed metabolites from being consumed without
    replacement, and requires strictly positive net formation of the focal
    target.  It is a stoichiometric feasibility filter, not growth or yield
    optimization.
    """
    if not selected_records:
        return {
            "supported": False,
            "net_target": 0.0,
            "target_consuming_reactions": [],
            "reaction_weights": {},
            "reason": "The candidate path contains no reactions.",
        }

    try:
        import numpy as np
        from scipy.optimize import linprog
    except ImportError as error:
        raise RuntimeError(
            "Alternative-path net-production filtering requires scipy."
        ) from error

    species_ids = sorted(
        {
            species_id
            for record in selected_records
            for key in ("reactants", "products")
            for species_id, _ in record[key]
        }
    )
    species_index = {species_id: index for index, species_id in enumerate(species_ids)}
    stoichiometry = np.zeros((len(species_ids), len(selected_records)), dtype=float)
    target_consuming_reactions: list[str] = []
    for column, record in enumerate(selected_records):
        for species_id, coefficient in record["reactants"]:
            stoichiometry[species_index[species_id], column] -= float(coefficient)
            if species_id == target_species_id:
                target_consuming_reactions.append(str(record["normalized_id"]))
        for species_id, coefficient in record["products"]:
            stoichiometry[species_index[species_id], column] += float(coefficient)

    if target_species_id not in species_index:
        return {
            "supported": False,
            "net_target": 0.0,
            "target_consuming_reactions": target_consuming_reactions,
            "reaction_weights": {},
            "reason": "The candidate path does not contain the focal target.",
        }

    inequality_rows: list[object] = []
    inequality_bounds: list[float] = []
    for species_id in species_ids:
        if species_id in seed_ids or species_id == target_species_id:
            continue
        inequality_rows.append(-stoichiometry[species_index[species_id], :])
        inequality_bounds.append(0.0)
    inequality_rows.append(-stoichiometry[species_index[target_species_id], :])
    inequality_bounds.append(-1.0)

    result = linprog(
        np.ones(len(selected_records), dtype=float),
        A_ub=np.asarray(inequality_rows, dtype=float),
        b_ub=np.asarray(inequality_bounds, dtype=float),
        bounds=[(1.0, None) for _ in selected_records],
        method="highs",
    )
    if not result.success:
        return {
            "supported": False,
            "net_target": 0.0,
            "target_consuming_reactions": target_consuming_reactions,
            "reaction_weights": {},
            "reason": (
                "The qualitative reaction set cannot be weighted to produce "
                "positive net target without consuming an unavailable "
                "non-seed metabolite."
            ),
        }

    target_row = stoichiometry[species_index[target_species_id], :]
    net_target = float(target_row @ result.x)
    reaction_weights = {
        str(record["normalized_id"]): float(result.x[index])
        for index, record in enumerate(selected_records)
    }
    return {
        "supported": net_target > 1e-9,
        "net_target": net_target,
        "target_consuming_reactions": target_consuming_reactions,
        "reaction_weights": reaction_weights,
        "reason": (
            "The directionally fixed reaction set supports positive net "
            "formation of the focal target."
        ),
    }


def path_root_precursors(
    model,
    selected_records: list[dict[str, object]],
    environmental_seed_ids: set[str],
    target_id: str,
) -> list[dict[str, object]]:
    produced_ids = {
        species_id
        for record in selected_records
        for species_id, _ in record["products"]
    }
    root_ids = {
        species_id
        for record in selected_records
        for species_id, _ in record["reactants"]
        if species_id in environmental_seed_ids and species_id not in produced_ids
    }
    roots: list[dict[str, object]] = []
    for species_id in sorted(root_ids):
        species = model.species[species_id]
        if (
            species.compartment == "e"
            and species.base_id not in NON_CANDIDATE_PRECURSORS
            and species.base_id != target_id
        ):
            roots.append(
                {
                    "base_id": species.base_id,
                    "species_id": species_id,
                    "name": species.name,
                    "selection_mode": "automatic_bounded_alternative_paths",
                }
            )
    return roots


def enumerate_alternative_paths(
    mene_path: Path,
    working_directory: Path,
    model,
    directed_records: list[dict[str, object]],
    seed_ids: set[str],
    environmental_seed_ids: set[str],
    target_species_id: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Enumerate alternative precursor-rooted paths without a known precursor.

    Every exchange-importable extracellular metabolite is initially available
    as a hypothetical precursor.  After MeneTools finds a path, each
    non-currency extracellular root used by that path is withheld in a child
    search.  This finds biologically different precursor alternatives without
    spending the search budget on many reaction-level variants of the same
    precursor route.  The rule is identical for every target and never receives
    a literature-expected precursor.
    """
    network_path = working_directory / "network.xml"
    target_path = working_directory / "target.xml"
    write_normalized_network(network_path, model, directed_records)
    write_species_document(
        target_path,
        model,
        {target_species_id},
        "step4_target",
    )

    seen_withheld_seed_sets: set[frozenset[str]] = set()
    seen_path_signatures: set[tuple[str, ...]] = set()
    queue: list[frozenset[str]] = [frozenset()]
    paths: list[dict[str, object]] = []
    solver_calls = 0
    minimum_size: int | None = None
    fallback_used = False
    record_by_id = {
        str(record["normalized_id"]): record for record in directed_records
    }

    def solve(withheld_seed_ids: frozenset[str]) -> dict[str, object] | None:
        nonlocal solver_calls, fallback_used
        if (
            withheld_seed_ids in seen_withheld_seed_sets
            or solver_calls >= MAX_PATH_SOLVER_CALLS
        ):
            return None
        seen_withheld_seed_sets.add(withheld_seed_ids)
        solver_calls += 1
        seed_path = working_directory / f"seeds_{solver_calls:04d}.xml"
        output_path = working_directory / f"mene_{solver_calls:04d}.json"
        active_seed_ids = seed_ids - set(withheld_seed_ids)
        write_species_document(
            seed_path,
            model,
            active_seed_ids,
            f"step4_seeds_{solver_calls:04d}",
        )
        result = run_menetools(
            mene_path,
            network_path,
            seed_path,
            target_path,
            output_path,
        )
        fallback_used = fallback_used or bool(
            result.get("menetools_compatibility_fallback", False)
        )
        selected_ids = tuple(sorted(str(value) for value in result.get("one_path", [])))
        if not selected_ids:
            return None
        selected_records = [
            record_by_id[reaction_id]
            for reaction_id in selected_ids
            if reaction_id in record_by_id
        ]
        if len(selected_records) != len(selected_ids):
            raise ValueError("MeneTools returned an unknown normalized reaction identifier.")
        return {
            "withheld_seed_ids": withheld_seed_ids,
            "signature": selected_ids,
            "records": selected_records,
            "reaction_count": len(selected_records),
        }

    while queue and len(paths) < MAX_ALTERNATIVE_PATHS and solver_calls < MAX_PATH_SOLVER_CALLS:
        withheld_seed_ids = queue.pop(0)
        state = solve(withheld_seed_ids)
        if state is None:
            continue
        signature = tuple(state["signature"])
        if minimum_size is None:
            minimum_size = int(state["reaction_count"])
        if signature not in seen_path_signatures:
            seen_path_signatures.add(signature)
            paths.append(state)

        produced_ids = {
            species_id
            for record in state["records"]
            for species_id, _ in record["products"]
        }
        used_root_ids = sorted(
            {
                species_id
                for record in state["records"]
                for species_id, _ in record["reactants"]
                if species_id in environmental_seed_ids
                and species_id not in produced_ids
                and model.species[species_id].base_id not in NON_CANDIDATE_PRECURSORS
                and species_id != target_species_id
            }
        )
        for species_id in used_root_ids:
            child = frozenset(set(withheld_seed_ids) | {species_id})
            if child not in seen_withheld_seed_sets and child not in queue:
                queue.append(child)

    paths.sort(
        key=lambda path: (
            int(path["reaction_count"]),
            tuple(path["signature"]),
        )
    )
    return paths, {
        "minimum_path_reaction_count": minimum_size or 0,
        "solver_calls": solver_calls,
        "search_truncated": bool(queue) or solver_calls >= MAX_PATH_SOLVER_CALLS,
        "menetools_compatibility_fallback": fallback_used,
    }


def main() -> None:
    args = parse_arguments()
    step3_path = args.step3_json.expanduser().resolve()
    diet_path = args.diet.expanduser().resolve()
    step3 = json.loads(step3_path.read_text(encoding="utf-8"))
    candidates = [row for row in step3["rows"] if row["decision"] == "Keep"]
    diet_bases = parse_diet(diet_path)
    rows: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    pathways: list[dict[str, object]] = []
    for candidate in candidates:
        model = load_model(candidate["model_path"])
        target_id = str(candidate["target_id"])
        target_species_ids = [
            value.strip()
            for value in str(candidate["internal_species_ids"]).split(";")
            if value.strip()
        ]
        if not target_species_ids:
            raise ValueError(f"No cytosolic target species for {candidate['model_file']} {target_id}")
        target_species_id = target_species_ids[0]
        exchanges = exchange_inventory(model)
        importable_bases = {
            str(record["base_id"])
            for record in exchanges
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
        seed_bases = (importable_bases & set(external_by_base)) - {target_id, "o2"}
        environmental_seed_ids = {external_by_base[base] for base in seed_bases}
        cofactor_seed_ids = {
            cytosolic_by_base[base]
            for base in COFACTOR_BOOTSTRAP
            if base != target_id and base in cytosolic_by_base
        }
        seed_ids = environmental_seed_ids | cofactor_seed_ids
        directed_records = directional_reaction_records(model)
        with tempfile.TemporaryDirectory(prefix="crossfeeding_step4_") as temporary_directory:
            temporary = Path(temporary_directory)
            path_states, search_metadata = enumerate_alternative_paths(
                args.mene.expanduser().resolve(),
                temporary,
                model,
                directed_records,
                seed_ids,
                environmental_seed_ids,
                target_species_id,
            )
        target_scope_reachable = bool(path_states)
        precursor_by_id: dict[str, dict[str, object]] = {}
        valid_path_states: list[dict[str, object]] = []
        all_target_reactions: list[dict[str, object]] = []

        for path_number, state in enumerate(path_states, start=1):
            path_id = f"{model.model_id}:{target_id}:path_{path_number:03d}"
            selected_records = list(state["records"])
            target_reactions = target_forming_reactions(
                selected_records,
                target_species_id,
            )
            feasibility = net_production_feasibility(
                selected_records,
                seed_ids,
                target_species_id,
            )
            path_roots = path_root_precursors(
                model,
                selected_records,
                environmental_seed_ids,
                target_id,
            )
            path_kept = bool(target_reactions) and bool(feasibility["supported"])
            if not target_reactions:
                path_reason = "No selected reaction forms the cytosolic target."
            elif not bool(feasibility["supported"]):
                path_reason = str(feasibility["reason"])
            else:
                path_reason = (
                    "The automatically discovered path supports positive net "
                    "target formation."
                )
            steps = pathway_steps(selected_records, seed_ids)
            reaction_weights = dict(feasibility["reaction_weights"])
            pathways.append(
                {
                    "path_id": path_id,
                    "model_file": candidate["model_file"],
                    "model_id": candidate["model_id"],
                    "bacterium": candidate["bacterium"],
                    "target_name": candidate["target_name"],
                    "target_id": target_id,
                    "reaction_count": len(selected_records),
                    "reaction_ids": "; ".join(
                        f"{record['reaction_id']} [{record['direction']}]"
                        for record in selected_records
                    ),
                    "target_forming_reactions": "; ".join(
                        f"{record['reaction_id']} [{record['direction']}]"
                        for record in target_reactions
                    ),
                    "target_consuming_reactions": "; ".join(
                        str(value)
                        for value in feasibility["target_consuming_reactions"]
                    ),
                    "net_target": float(feasibility["net_target"]),
                    "precursor_candidate_ids": "; ".join(
                        str(root["base_id"]) for root in path_roots
                    ),
                    "precursor_candidate_names": "; ".join(
                        str(root["name"]) for root in path_roots
                    ),
                    "decision": "Keep" if path_kept else "Exclude",
                    "reason": path_reason,
                }
            )
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
                        "path_id": path_id,
                        "path_decision": "Keep" if path_kept else "Exclude",
                        "model_file": candidate["model_file"],
                        "model_id": candidate["model_id"],
                        "bacterium": candidate["bacterium"],
                        "target_name": candidate["target_name"],
                        "target_id": target_id,
                        "path_step": steps.get(normalized_id),
                        "reaction_id": record["reaction_id"],
                        "reaction_name": record["reaction_name"],
                        "direction": record["direction"],
                        "equation": record["equation"],
                        "reaction_weight": reaction_weights.get(normalized_id),
                        "forms_target_inside_cell": normalized_id
                        in target_normalized_ids,
                        "evidence_scope": "automatic_bounded_alternative_path",
                    }
                )
            if not path_kept:
                continue
            state["path_id"] = path_id
            state["roots"] = path_roots
            state["feasibility"] = feasibility
            valid_path_states.append(state)
            all_target_reactions.extend(target_reactions)
            for root in path_roots:
                precursor_id = str(root["base_id"])
                if precursor_id not in precursor_by_id:
                    precursor_by_id[precursor_id] = {
                        **root,
                        "path_ids": [],
                    }
                precursor_by_id[precursor_id]["path_ids"].append(path_id)

        precursor_candidates = [
            {
                **precursor,
                "path_ids": sorted(str(value) for value in precursor["path_ids"]),
            }
            for precursor in sorted(
                precursor_by_id.values(),
                key=lambda value: str(value["base_id"]),
            )
        ]
        internally_producible = bool(valid_path_states)
        representative_records = (
            list(valid_path_states[0]["records"])
            if valid_path_states
            else (list(path_states[0]["records"]) if path_states else [])
        )
        decision = "Keep" if internally_producible else "Exclude"
        if internally_producible:
            reason = (
                "At least one automatically discovered target-withheld path "
                "passed the positive-net-target filter."
            )
        elif target_scope_reachable:
            reason = (
                "MeneTools found qualitative target paths, but all enumerated "
                "paths failed the net-production filter."
            )
        else:
            reason = "The cytosolic target was not reachable from the target-withheld seed set."
        rows.append(
            {
                "model_file": candidate["model_file"],
                "model_path": candidate["model_path"],
                "model_id": candidate["model_id"],
                "bacterium": candidate["bacterium"],
                "target_name": candidate["target_name"],
                "target_id": target_id,
                "host_relevance": candidate["host_relevance"],
                "metabolite_class": candidate["metabolite_class"],
                "microbial_evidence": candidate["microbial_evidence"],
                "selection_rationale": candidate["selection_rationale"],
                "reference": candidate["reference"],
                "target_species_id": target_species_id,
                "environmental_seed_count": len(environmental_seed_ids),
                "cofactor_bootstrap_count": len(cofactor_seed_ids),
                "target_withheld": True,
                "mene_target_reachable": target_scope_reachable,
                "intracellular_production_reactions": "; ".join(
                    sorted(
                        {
                            f"{record['reaction_id']} [{record['direction']}]"
                            for record in all_target_reactions
                        }
                    )
                ),
                "minimum_path_reaction_count": search_metadata[
                    "minimum_path_reaction_count"
                ],
                "alternative_paths_found": len(path_states),
                "net_positive_paths": len(valid_path_states),
                "paths_rejected": len(path_states) - len(valid_path_states),
                "path_solver_calls": search_metadata["solver_calls"],
                "path_search_truncated": search_metadata["search_truncated"],
                "menetools_compatibility_fallback": bool(
                    search_metadata["menetools_compatibility_fallback"]
                ),
                "representative_path_reactions": "; ".join(
                    f"{record['reaction_id']} [{record['direction']}]"
                    for record in representative_records
                ),
                "precursor_candidate_ids": "; ".join(
                    str(record["base_id"]) for record in precursor_candidates
                ),
                "precursor_candidate_names": "; ".join(
                    str(record["name"]) for record in precursor_candidates
                ),
                "precursor_candidates": precursor_candidates,
                "decision": decision,
                "reason": reason,
            }
        )
    kept_rows = [row for row in rows if row["decision"] == "Keep"]
    result = {
        "metadata": {
            "analysis": "Step 4 target-withheld intracellular production screen",
            "method": (
                "MeneTools target-withheld qualitative paths on "
                "FBC-direction-normalized SBML, followed by a generic "
                "stoichiometric positive-net-target feasibility filter"
            ),
            "menetools_version": menetools_version(args.mene.expanduser().resolve()),
            "condition": args.condition_label,
            "seed_rule": (
                "Every extracellular metabolite with import-capable exchange is "
                "available as a hypothetical precursor; focal target and oxygen "
                "are withheld. Diet membership is reported as context but does not "
                "restrict precursor discovery."
            ),
            "cofactor_rule": (
                "Selected cytosolic currency cofactors are bootstrapped only to "
                "break Boolean cycles. Reduced redox carriers (NADH, NADPH and "
                "FADH2) are not bootstrapped, so a candidate route must generate "
                "the reducing power it uses."
            ),
            "path_enumeration_rule": (
                "Alternative precursor-rooted paths are discovered without an "
                "expected precursor by repeatedly withholding extracellular roots "
                f"used by prior paths; retain up to {MAX_ALTERNATIVE_PATHS} paths "
                f"using at most {MAX_PATH_SOLVER_CALLS} MeneTools calls"
            ),
            "net_production_rule": (
                "Every selected reaction has positive weight; supplied seeds may "
                "be consumed; non-seed metabolites cannot have negative net "
                "production; the focal target must have positive net production"
            ),
            "precursor_rule": (
                "Automatically nominate non-currency extracellular root seeds "
                "from net-positive paths; no literature-expected precursor or "
                "strain is supplied to discovery"
            ),
            "step3_input": str(step3_path),
            "diet_file": str(diet_path),
        },
        "summary": {
            "step3_candidates_tested": len(rows),
            "kept": len(kept_rows),
            "excluded": len(rows) - len(kept_rows),
            "models_with_at_least_one_production_candidate": len(
                {row["model_id"] for row in kept_rows}
            ),
        },
        "rows": rows,
        "pathways": pathways,
        "evidence": evidence,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.xlsx_output:
        write_workbook(result, args.xlsx_output, "step4")
    print(f"step3_candidates_tested\t{len(rows)}")
    print(f"kept\t{len(kept_rows)}")
    print(f"excluded\t{len(rows) - len(kept_rows)}")
    print(f"json\t{args.json_output}")
    if args.xlsx_output:
        print(f"xlsx\t{args.xlsx_output}")


if __name__ == "__main__":
    main()

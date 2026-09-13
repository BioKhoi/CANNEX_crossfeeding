#!/usr/bin/env python3
"""Run the six-stage target-guided potential cross-feeding workflow."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


RELEASE_DIRECTORY = Path(__file__).resolve().parent
SOURCE_DIRECTORY = RELEASE_DIRECTORY / "src"
CONFIG_DIRECTORY = RELEASE_DIRECTORY / "config"
DEFAULT_TARGETS = CONFIG_DIRECTORY / "clinical_targets.tsv"
DEFAULT_DIET = CONFIG_DIRECTORY / "HighFiberDietAGORA2.txt"
DEFAULT_MANIFEST = CONFIG_DIRECTORY / "model_manifest.tsv"
CONDITION_LABEL = "HighFiber AGORA2 diet; anaerobic (oxygen withheld)"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Identify GEM-supported potential donor-precursor-recipient-target "
            "routes for user-selected microbial metabolites. This is a qualitative, "
            "non-flux workflow and does not confirm realized cross-feeding."
        )
    )
    parser.add_argument("--gem-dir", type=Path, required=True)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Final .xlsx path. Required for analysis runs so output creation is "
            "always explicit; not required with --check-only."
        ),
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate inputs, dependencies, and model checksums without analysis.",
    )
    return parser.parse_args()


def resolve_mene() -> Path:
    # Keep the virtual-environment bin/Scripts directory. Resolving a symlinked
    # Python executable can jump back to the system installation and hide the
    # adjacent MeneTools launcher.
    executable_directory = Path(sys.executable).expanduser().absolute().parent
    path_candidate = shutil.which("mene")
    candidates = [
        *([Path(path_candidate)] if path_candidate else []),
        executable_directory / "mene",
        executable_directory / "mene.exe",
    ]
    for candidate in candidates:
        path = candidate.resolve()
        if path.is_file():
            return path
    raise FileNotFoundError(
        "MeneTools executable was not found. Activate the project environment "
        "created from environment.yml or requirements.txt."
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"model_file", "model_id", "species", "strain", "sha256", "source"}
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


def resolve_manifest(gem_directory: Path, supplied_names: set[str]) -> Path:
    """Select the manifest that exactly describes the supplied GEM directory."""
    candidates = [
        gem_directory / "model_manifest.tsv",
        gem_directory.parent / "config" / "model_manifest.tsv",
        DEFAULT_MANIFEST.resolve(),
    ]
    checked: list[str] = []
    for candidate in candidates:
        candidate = candidate.resolve()
        if str(candidate) in checked or not candidate.is_file():
            continue
        checked.append(str(candidate))
        if set(read_manifest(candidate)) == supplied_names:
            return candidate
    locations = ", ".join(checked) if checked else "none found"
    raise ValueError(
        "No model manifest exactly matches the supplied GEM files. "
        "Create one with 'python create_model_manifest.py --gem-dir <GEM_FOLDER>'. "
        "The runner accepts <GEM_FOLDER>/model_manifest.tsv, a case manifest at "
        f"<case>/config/model_manifest.tsv, or the bundled manuscript manifest. "
        f"Checked: {locations}"
    )


def validate_setup(args: argparse.Namespace) -> dict[str, Any]:
    gem_directory = args.gem_dir.expanduser().resolve()
    targets = args.targets.expanduser().resolve()
    diet = DEFAULT_DIET.resolve()
    mene = resolve_mene()

    if not gem_directory.is_dir():
        raise FileNotFoundError(f"GEM directory was not found: {gem_directory}")
    for label, path in (
        ("target table", targets),
        ("diet file", diet),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"The {label} was not found: {path}")
    required_scripts = (
        "sbml_structural.py",
        "workbook_writer.py",
        "step1_target_selection.py",
        "step2_exchange_screen.py",
        "step3_transport_screen.py",
        "step4_intracellular_production.py",
        "step5_precursor_import.py",
        "step6_cross_species_donor.py",
    )
    missing_scripts = [name for name in required_scripts if not (SOURCE_DIRECTORY / name).is_file()]
    if missing_scripts:
        raise FileNotFoundError(
            "Release script(s) missing: " + ", ".join(missing_scripts)
        )

    gem_files = sorted(gem_directory.glob("*.xml"))
    if not gem_files:
        raise FileNotFoundError(f"No XML GEMs found in: {gem_directory}")
    supplied_names = {path.name for path in gem_files}
    manifest_path = resolve_manifest(gem_directory, supplied_names)
    manifest = read_manifest(manifest_path)
    manifest_names = set(manifest)
    unlisted = sorted(supplied_names - manifest_names)
    missing = sorted(manifest_names - supplied_names)
    if unlisted or missing:
        details = []
        if unlisted:
            details.append("unlisted GEMs: " + ", ".join(unlisted))
        if missing:
            details.append("manifest GEMs not supplied: " + ", ".join(missing))
        raise ValueError("GEM/manifest mismatch; " + "; ".join(details))
    mismatched = [
        path.name
        for path in gem_files
        if sha256(path).casefold() != manifest[path.name]["sha256"].casefold()
    ]
    if mismatched:
        raise ValueError("GEM checksum mismatch: " + ", ".join(mismatched))

    try:
        import openpyxl  # noqa: F401
    except ImportError as error:
        raise RuntimeError(
            "The public Excel dependency openpyxl is missing. Install environment.yml."
        ) from error

    sys.path.insert(0, str(SOURCE_DIRECTORY))
    from step1_target_selection import read_targets

    read_targets(targets)

    adjacent_clingo = (
        mene.parent / "clingo",
        mene.parent / "clingo.exe",
    )
    if not any(path.is_file() for path in adjacent_clingo) and not shutil.which("clingo"):
        raise FileNotFoundError(
            "Clingo, required by MeneTools, was not found beside MeneTools or on PATH."
        )
    return {
        "gem_directory": gem_directory,
        "gem_files": gem_files,
        "targets": targets,
        "diet": diet,
        "manifest": manifest_path,
        "mene": mene,
    }


def run_stage(script_name: str, arguments: list[str]) -> None:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = "0"
    completed = subprocess.run(
        [sys.executable, str(SOURCE_DIRECTORY / script_name), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{script_name} failed with exit code {completed.returncode}:\n"
            + completed.stdout[-5000:]
        )


def sanitize_paths(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if key.endswith("_input") and isinstance(item, str):
                sanitized[key] = "Temporary pipeline output; not retained"
            elif key.endswith("_path") and isinstance(item, str):
                sanitized[key] = Path(item).name
            elif key in {"gem_directory", "diet_file", "model_manifest"} and isinstance(item, str):
                sanitized[key] = Path(item).name
            else:
                sanitized[key] = sanitize_paths(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_paths(item) for item in value]
    return value


def build_consumer_audits(
    stage_documents: list[dict[str, Any]],
    gem_directory: Path,
) -> list[dict[str, Any]]:
    """Retain unbiased consumer pass/null evidence for every model-target test."""
    if len(stage_documents) < 5:
        raise ValueError("Consumer auditing requires Steps 1 through 5.")

    step2, step3, step4, step5 = stage_documents[1:5]

    def index_rows(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
        return {
            (str(row["model_id"]), str(row["target_id"])): row
            for row in document.get("rows", [])
        }

    step3_rows = index_rows(step3)
    step4_rows = index_rows(step4)
    step5_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in step5.get("rows", []):
        key = (str(row["model_id"]), str(row["target_id"]))
        step5_rows.setdefault(key, []).append(row)
    audits: list[dict[str, Any]] = []

    for step2_row in step2.get("rows", []):
        key = (str(step2_row["model_id"]), str(step2_row["target_id"]))
        step3_row = step3_rows.get(key)
        step4_row = step4_rows.get(key)
        precursor_rows = step5_rows.get(key, [])
        retained_precursors = [
            row for row in precursor_rows if row.get("decision") == "Keep"
        ]

        target_exchange_export = step2_row.get("decision") == "Keep"
        target_outward_transport = bool(
            step3_row and step3_row.get("decision") == "Keep"
        )
        target_internal_production = bool(
            step4_row and step4_row.get("decision") == "Keep"
        )
        precursor_import = bool(retained_precursors)
        consumer_pass = all(
            (
                target_exchange_export,
                target_outward_transport,
                target_internal_production,
                precursor_import,
            )
        )
        failed_requirements = [
            label
            for label, passed in (
                ("target exchange export", target_exchange_export),
                ("target outward transport", target_outward_transport),
                ("target intracellular production", target_internal_production),
                ("at least one automatically discovered importable precursor", precursor_import),
            )
            if not passed
        ]
        audits.append(
            {
                "model_file": step2_row["model_file"],
                "model_id": step2_row["model_id"],
                "consumer_bacterium": step2_row["bacterium"],
                "target_name": step2_row["target_name"],
                "target_id": step2_row["target_id"],
                "target_exchange_export_pass": target_exchange_export,
                "target_outward_transport_pass": target_outward_transport,
                "target_internal_production_pass": target_internal_production,
                "alternative_paths_found": (
                    int(step4_row.get("alternative_paths_found", 0))
                    if step4_row
                    else 0
                ),
                "net_positive_paths": (
                    int(step4_row.get("net_positive_paths", 0))
                    if step4_row
                    else 0
                ),
                "paths_rejected": (
                    int(step4_row.get("paths_rejected", 0))
                    if step4_row
                    else 0
                ),
                "path_solver_calls": (
                    int(step4_row.get("path_solver_calls", 0))
                    if step4_row
                    else 0
                ),
                "path_search_truncated": (
                    bool(step4_row.get("path_search_truncated", False))
                    if step4_row
                    else False
                ),
                "discovered_precursor_ids": (
                    str(step4_row.get("precursor_candidate_ids", ""))
                    if step4_row
                    else ""
                ),
                "precursor_import_tests": len(precursor_rows),
                "importable_precursor_ids": "; ".join(
                    sorted(str(row["precursor_id"]) for row in retained_precursors)
                ),
                "precursor_import_screen_pass": precursor_import,
                "consumer_pass": consumer_pass,
                "decision": "Keep" if consumer_pass else "Exclude",
                "reason": (
                    "The consumer has target exchange and outward transport, at "
                    "least one net-positive target-production path, and at least "
                    "one automatically discovered importable precursor."
                    if consumer_pass
                    else "Failed requirement(s): " + "; ".join(failed_requirements)
                ),
            }
        )
    return sorted(
        audits,
        key=lambda row: (
            str(row["target_id"]),
            str(row["consumer_bacterium"]),
        ),
    )


def run_pipeline(args: argparse.Namespace, setup: dict[str, Any]) -> tuple[Path, Path, dict[str, Any], float]:
    if not args.output:
        raise ValueError("--output is required unless --check-only is used.")
    output = args.output.expanduser().resolve()
    if output.suffix.casefold() != ".xlsx":
        raise ValueError(f"Final output must use the .xlsx extension: {output}")
    output_json = output.with_suffix(".json")
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="crossfeeding_") as temporary_text:
        temporary = Path(temporary_text)
        stage_json = [temporary / f"step{index}.json" for index in range(1, 7)]
        stages = [
            (
                "[1/6] Validating literature-guided user-selected metabolites",
                "step1_target_selection.py",
                [
                    "--gem-dir", str(setup["gem_directory"]),
                    "--targets", str(setup["targets"]),
                    "--json-output", str(stage_json[0]),
                ],
            ),
            (
                "[2/6] Screening target exchange export",
                "step2_exchange_screen.py",
                [
                    "--gem-dir", str(setup["gem_directory"]),
                    "--step1-json", str(stage_json[0]),
                    "--json-output", str(stage_json[1]),
                ],
            ),
            (
                "[3/6] Screening outward target transport",
                "step3_transport_screen.py",
                [
                    "--step2-json", str(stage_json[1]),
                    "--json-output", str(stage_json[2]),
                ],
            ),
            (
                "[4/6] Testing target-withheld intracellular production",
                "step4_intracellular_production.py",
                [
                    "--step3-json", str(stage_json[2]),
                    "--diet", str(setup["diet"]),
                    "--mene", str(setup["mene"]),
                    "--condition-label", CONDITION_LABEL,
                    "--json-output", str(stage_json[3]),
                ],
            ),
            (
                "[5/6] Screening recipient precursor import",
                "step5_precursor_import.py",
                [
                    "--step4-json", str(stage_json[3]),
                    "--json-output", str(stage_json[4]),
                ],
            ),
            (
                "[6/6] Testing cross-species precursor donors",
                "step6_cross_species_donor.py",
                [
                    "--step5-json", str(stage_json[4]),
                    "--gem-dir", str(setup["gem_directory"]),
                    "--model-manifest", str(setup["manifest"]),
                    "--diet", str(setup["diet"]),
                    "--mene", str(setup["mene"]),
                    "--condition-label", CONDITION_LABEL,
                    "--json-output", str(stage_json[5]),
                ],
            ),
        ]
        for message, script, arguments in stages:
            print(message, flush=True)
            run_stage(script, arguments)
        stage_documents = [
            json.loads(path.read_text(encoding="utf-8")) for path in stage_json
        ]
        result = stage_documents[5]
        result["pathways"] = list(stage_documents[3].get("pathways", []))
        consumer_audits = build_consumer_audits(
            stage_documents,
            setup["gem_directory"],
        )
        result["consumer_audits"] = consumer_audits
        result["summary"]["consumers_audited"] = len(consumer_audits)
        result["summary"]["consumers_kept"] = sum(
            row["decision"] == "Keep" for row in consumer_audits
        )

    result = sanitize_paths(result)
    result["metadata"]["pipeline_runner"] = "find_crossfeeding.py"
    result["metadata"]["path_reproducibility"] = (
        "Each scientific stage runs with PYTHONHASHSEED=0. Together with the "
        "pinned MeneTools and Clingo versions, this makes the fixed bounded "
        "precursor-root-withholding alternative-path search reproducible; the "
        "search never receives a literature-expected precursor or strain."
    )
    result["metadata"]["intermediate_outputs"] = "Temporary; not retained"
    result["metadata"]["interpretation"] = (
        "Retained rows are GEM-supported potential cross-species precursor-supply "
        "edges under qualitative non-flux rules; they are not confirmed cross-feeding."
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    sys.path.insert(0, str(SOURCE_DIRECTORY))
    from workbook_writer import write_workbook

    write_workbook(result, output, "step6")
    return output, output_json, result, time.perf_counter() - started


def main() -> int:
    args = parse_arguments()
    try:
        setup = validate_setup(args)
        if args.check_only:
            print("Cross-feeding workflow setup is ready")
            print(f"Python: {Path(sys.executable).resolve()}")
            print(f"Input GEMs: {len(setup['gem_files'])}")
            print(f"Targets: {setup['targets'].name}")
            print(f"Model manifest: {setup['manifest'].name}")
            print(f"MeneTools: {setup['mene']}")
            return 0
        output, output_json, result, elapsed = run_pipeline(args, setup)
    except KeyboardInterrupt:
        print("Analysis cancelled.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Potential cross-feeding workflow completed")
    print(f"Potential edges retained: {result['summary']['potential_edges_kept']}")
    print(f"Elapsed seconds: {elapsed:.2f}")
    print(f"Excel: {output}")
    print(f"JSON: {output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

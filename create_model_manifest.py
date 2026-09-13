#!/usr/bin/env python3
"""Create a checksum-verified model manifest for an AGORA2-compatible GEM set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import tempfile
from pathlib import Path


RELEASE_DIRECTORY = Path(__file__).resolve().parent
SOURCE_DIRECTORY = RELEASE_DIRECTORY / "src"
sys.path.insert(0, str(SOURCE_DIRECTORY))

from sbml_structural import load_model  # noqa: E402


FIELDNAMES = [
    "model_file",
    "model_id",
    "species",
    "strain",
    "sha256",
    "source",
    "redistributed",
    "model_name",
    "compartments",
    "metadata_status",
]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate model_manifest.tsv for a folder of AGORA2-compatible "
            "SBML GEMs. Species and strain are inferred from each SBML model "
            "name and must be reviewed before publication. Cytosol and "
            "extracellular compartments are required; an optional periplasm "
            "is detected and recorded for Gram-negative models."
        )
    )
    parser.add_argument("--gem-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        help="Manifest path; defaults to <gem-dir>/model_manifest.tsv.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing generated manifest after rechecking all GEMs.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_model_name(model_name: str, fallback: str) -> str:
    value = model_name.strip() or fallback
    return " ".join(value.replace("_", " ").split())


def infer_species_and_strain(model_name: str) -> tuple[str, str]:
    """Infer a consistent species key and strain label from an SBML model name."""
    tokens = model_name.split()
    if not tokens:
        return "not specified", "not specified"
    if tokens[0].casefold() == "candidatus" and len(tokens) >= 3:
        species_width = 3
    elif len(tokens) >= 2:
        species_width = 2
    else:
        species_width = 1
    species = " ".join(tokens[:species_width])
    strain = " ".join(tokens[species_width:]) or "not specified"
    return species, strain


def infer_source(path: Path) -> str:
    with path.open("rb") as handle:
        head = handle.read(128 * 1024).decode("utf-8", errors="replace")
    obtained_match = re.search(
        r"Obtained\s+from\s+([^<\r\n]+)",
        head,
        flags=re.IGNORECASE,
    )
    obtained = obtained_match.group(1).strip() if obtained_match else "not encoded"
    if "AGORA2" in head or "AGORA2:" in head:
        return (
            "AGORA2-compatible SBML inferred from model annotation; "
            f"annotation source: {obtained}; verify database version and URL"
        )
    return (
        "User-supplied SBML; "
        f"annotation source: {obtained}; verify database, version, and URL"
    )


def build_manifest_rows(gem_directory: Path) -> list[dict[str, str]]:
    gem_files = sorted(gem_directory.glob("*.xml"), key=lambda path: path.name.casefold())
    if not gem_files:
        raise FileNotFoundError(f"No .xml GEM files were found in: {gem_directory}")

    rows: list[dict[str, str]] = []
    failures: list[str] = []
    observed_model_ids: dict[str, str] = {}
    for path in gem_files:
        try:
            model = load_model(path)
        except Exception as error:
            failures.append(f"{path.name}: invalid or unreadable SBML ({error})")
            continue
        compartments = sorted(
            {record.compartment for record in model.species.values() if record.compartment}
        )
        missing_compartments = sorted({"c", "e"} - set(compartments))
        if missing_compartments:
            failures.append(
                f"{path.name}: missing required compartment(s) "
                + ", ".join(missing_compartments)
            )
            continue
        if model.model_id in observed_model_ids:
            failures.append(
                f"{path.name}: duplicate model_id {model.model_id!r}; also used by "
                f"{observed_model_ids[model.model_id]}"
            )
            continue
        observed_model_ids[model.model_id] = path.name
        model_name = normalized_model_name(model.model_name, path.stem)
        species, strain = infer_species_and_strain(model_name)
        rows.append(
            {
                "model_file": path.name,
                "model_id": model.model_id,
                "species": species,
                "strain": strain,
                "sha256": sha256(path),
                "source": infer_source(path),
                "redistributed": "not assessed; user must verify",
                "model_name": model_name,
                "compartments": "; ".join(compartments),
                "metadata_status": (
                    "automatic draft; verify species, strain, source, and "
                    "redistribution before publication"
                ),
            }
        )
    if failures:
        raise ValueError(
            "Manifest was not created because one or more GEMs failed validation:\n- "
            + "\n- ".join(failures)
        )
    return rows


def write_manifest(
    gem_directory: Path,
    output: Path,
    overwrite: bool = False,
) -> list[dict[str, str]]:
    gem_directory = gem_directory.expanduser().resolve()
    output = output.expanduser().resolve()
    if not gem_directory.is_dir():
        raise FileNotFoundError(f"GEM directory was not found: {gem_directory}")
    if output.exists() and not overwrite:
        raise FileExistsError(
            f"Manifest already exists: {output}. Review it or rerun with --overwrite."
        )
    rows = build_manifest_rows(gem_directory)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as handle:
            temporary_name = handle.name
            writer = csv.DictWriter(
                handle,
                fieldnames=FIELDNAMES,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        Path(temporary_name).replace(output)
    finally:
        if temporary_name:
            temporary_path = Path(temporary_name)
            if temporary_path.exists():
                temporary_path.unlink()
    return rows


def main() -> int:
    args = parse_arguments()
    gem_directory = args.gem_dir.expanduser().resolve()
    output = (
        args.output.expanduser().resolve()
        if args.output
        else gem_directory / "model_manifest.tsv"
    )
    try:
        rows = write_manifest(gem_directory, output, overwrite=args.overwrite)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Model manifest created")
    print(f"Validated GEMs: {len(rows)}")
    print(f"Manifest: {output}")
    print(
        "Review species, strain, source, and redistribution columns before "
        "publication; checksums and SBML model IDs were generated automatically."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

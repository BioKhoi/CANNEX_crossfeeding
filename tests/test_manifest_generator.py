from __future__ import annotations

import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

import create_model_manifest
import find_crossfeeding


def synthetic_sbml(model_id: str, model_name: str, compartments=("c", "e")) -> str:
    compartment_xml = "".join(
        f'<compartment id="{value}" constant="true"/>' for value in compartments
    )
    species_xml = "".join(
        f'<species id="M_test__91__{value}__93__" name="Test" '
        f'compartment="{value}" boundaryCondition="false" constant="false"/>'
        for value in compartments
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<sbml xmlns="http://www.sbml.org/sbml/level3/version1/core" level="3" version="1">
  <model id="{model_id}" name="{model_name}">
    <annotation><notes><body xmlns="http://www.w3.org/1999/xhtml">
      <p>AGORA2: test annotation</p><p>Obtained from https://vmh.life/</p>
    </body></notes></annotation>
    <listOfCompartments>{compartment_xml}</listOfCompartments>
    <listOfSpecies>{species_xml}</listOfSpecies>
  </model>
</sbml>
'''


class ManifestGeneratorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.gem_directory = Path(self.temporary.name) / "models"
        self.gem_directory.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def add_model(
        self,
        filename: str,
        model_id: str,
        model_name: str,
        compartments=("c", "e"),
    ) -> Path:
        path = self.gem_directory / filename
        path.write_text(
            synthetic_sbml(model_id, model_name, compartments),
            encoding="utf-8",
        )
        return path

    def test_generates_checksums_and_inferred_metadata(self) -> None:
        first = self.add_model(
            "Bifidobacterium_adolescentis_L2_32.xml",
            "M_Bifidobacterium_adolescentis_L2_32",
            "Bifidobacterium adolescentis L2 32",
        )
        self.add_model(
            "Faecalibacterium_prausnitzii_A2_165.xml",
            "M_Faecalibacterium_prausnitzii_A2_165",
            "Faecalibacterium prausnitzii A2 165",
        )
        output = self.gem_directory / "model_manifest.tsv"
        rows = create_model_manifest.write_manifest(self.gem_directory, output)
        self.assertEqual(len(rows), 2)
        with output.open(encoding="utf-8", newline="") as handle:
            saved = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(saved[0]["species"], "Bifidobacterium adolescentis")
        self.assertEqual(saved[0]["strain"], "L2 32")
        self.assertEqual(
            saved[0]["sha256"], hashlib.sha256(first.read_bytes()).hexdigest()
        )
        self.assertIn("automatic draft", saved[0]["metadata_status"])
        self.assertEqual(
            find_crossfeeding.resolve_manifest(
                self.gem_directory,
                {path.name for path in self.gem_directory.glob("*.xml")},
            ),
            output.resolve(),
        )

    def test_refuses_to_overwrite_without_explicit_permission(self) -> None:
        self.add_model("model.xml", "M_model", "Example bacterium strain1")
        output = self.gem_directory / "model_manifest.tsv"
        create_model_manifest.write_manifest(self.gem_directory, output)
        with self.assertRaisesRegex(FileExistsError, "already exists"):
            create_model_manifest.write_manifest(self.gem_directory, output)

    def test_records_optional_periplasm_for_gram_negative_model(self) -> None:
        self.add_model(
            "Proteus_mirabilis_HI4320.xml",
            "M_Proteus_mirabilis_HI4320",
            "Proteus mirabilis HI4320",
            ("c", "p", "e"),
        )
        output = self.gem_directory / "model_manifest.tsv"
        rows = create_model_manifest.write_manifest(self.gem_directory, output)
        self.assertEqual(rows[0]["species"], "Proteus mirabilis")
        self.assertEqual(rows[0]["strain"], "HI4320")
        self.assertEqual(rows[0]["compartments"], "c; e; p")

    def test_duplicate_model_ids_stop_manifest_creation(self) -> None:
        self.add_model("first.xml", "M_duplicate", "Example bacterium strain1")
        self.add_model("second.xml", "M_duplicate", "Example bacterium strain2")
        output = self.gem_directory / "model_manifest.tsv"
        with self.assertRaisesRegex(ValueError, "duplicate model_id"):
            create_model_manifest.write_manifest(self.gem_directory, output)
        self.assertFalse(output.exists())

    def test_missing_required_compartment_stops_manifest_creation(self) -> None:
        path = self.gem_directory / "missing_e.xml"
        path.write_text(
            synthetic_sbml("M_missing_e", "Example bacterium strain", ("c",)),
            encoding="utf-8",
        )
        output = self.gem_directory / "model_manifest.tsv"
        with self.assertRaisesRegex(ValueError, "missing required compartment"):
            create_model_manifest.write_manifest(self.gem_directory, output)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

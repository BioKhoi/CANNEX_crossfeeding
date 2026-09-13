# Optional model input directory

This directory remains an optional extraction/download location for the small
five-model regression example. On Windows, `windows/setup_and_test.ps1`
downloads those exact files from the official AGORA2 v2.01 individual-SBML
directory and verifies each SHA-256 checksum against
`config/model_manifest.tsv`.

The complete locked input panels for the two saved CANNEX analyses are
distributed separately as `CANNEX_study/core6/models.zip` and
`CANNEX_study/core15/models.zip`. Each archive contains its own matching model
manifest and should be extracted into a separate empty directory.

Users who obtain the models separately can place exactly these five files in
this directory and run:

```text
python find_crossfeeding.py --gem-dir models --check-only
```

Do not rename or modify the XML files. The setup check rejects missing,
additional, or checksum-mismatched models.

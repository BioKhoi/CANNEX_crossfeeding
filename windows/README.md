# Testing the cross-feeding workflow on Windows

## Requirements

- 64-bit Windows 10 or Windows 11
- Internet access for the first setup
- 64-bit Miniconda or Anaconda

No R installation is needed to test the scientific Python workflow.

## Default compatibility test

1. Extract the ZIP to a local folder, preferably a short path such as
   `C:\crossfeeding_workflow`.
2. Double-click `windows\RUN_WINDOWS_TEST.bat`.
3. Keep the terminal open until the final success or error message appears.

The first run:

- downloads the exact five official AGORA2 v2.01 XML files;
- verifies every model checksum;
- creates the pinned `crossfeeding-workflow` Conda environment;
- validates inputs and dependencies;
- runs the synthetic and release tests.

The default test does not run the six-stage analysis and does not create an
Excel, JSON, CSV, or figure output.

## Full analysis and manuscript-edge regression

Open Anaconda Prompt in the extracted release folder and run:

```bat
windows\RUN_WINDOWS_TEST.bat -FullAnalysis
```

This explicit option creates:

```text
outputs\windows_test_results.xlsx
outputs\windows_test_results.json
```

It then verifies retained edge identities against
`config\expected_manuscript_edges.tsv`. The bundled file is still the earlier
ten-edge snapshot. Relock it after biological review of the current generalized
workflow output before using `-FullAnalysis` as the final manuscript regression.

## What to send back after testing

Please report:

- Windows version;
- whether the default test passed;
- the number of edges retained by `-FullAnalysis` and whether the regression
  passed against the manuscript-locked edge file;
- the complete terminal error text if anything failed.

The R figure is optional and is not part of this Windows compatibility test.

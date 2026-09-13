# Testing the cross-feeding workflow on Windows

## Requirements

- 64-bit Windows 10 or Windows 11
- Internet access for the first environment setup
- 64-bit Miniconda or Anaconda

No R installation is needed to test the scientific Python workflow.

## Default compatibility test

1. Download or clone the repository to a local folder, preferably a short path
   such as `C:\crossfeeding_workflow`.
2. Double-click `windows\RUN_WINDOWS_TEST.bat`.
3. Keep the terminal open until the final success or error message appears.

The first run:

- creates the pinned `crossfeeding-workflow` Conda environment;
- checks Python, MeneTools and Clingo;
- validates the bundled Validation Case 01 GEMs, manifest and target table;
- runs the automated tests; and
- checks the seven locked validation comparisons.

The default test does not create a new Excel or JSON result.

## Run the complete Case 01 tutorial

Open Anaconda Prompt in the repository folder and run:

```bat
windows\RUN_WINDOWS_TEST.bat -FullAnalysis
```

This creates:

```text
outputs\case01_windows_test.xlsx
outputs\case01_windows_test.json
```

The workbook is the same user-facing potential-edge output described in the
main README. The Case 01 GEMs are already included under `validation\cases`;
the Windows launcher does not download a separate development model panel.

## What to send back after testing

Please report:

- Windows version;
- whether the default test passed;
- the number of Case 01 edges retained by `-FullAnalysis`; and
- the complete terminal error text if anything failed.

The R visualization is separate and is not part of this Windows compatibility
test.

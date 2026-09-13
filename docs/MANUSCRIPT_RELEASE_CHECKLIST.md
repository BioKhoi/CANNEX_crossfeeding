# Manuscript software release checklist

Status checked on 2026-09-12. This checklist applies only to the scripts and
cross-feeding validation materials in this prototype.

## Completed technical checks

- Main Python entry point is `find_crossfeeding.py`; no computer-specific path
  is embedded in the scripts, saved JSON files or saved Excel workbooks.
- Dependencies are pinned consistently in `requirements.txt` and
  `environment.yml`.
- All 28 automated tests pass when no external manuscript-result regression is
  requested; the optional external-result test is intentionally skipped.
- All eight retained validation folders pass dependency, manifest and SHA-256
  checksum setup checks.
- All seven formal literature/control comparisons pass.
- The two incomplete IPA and deoxycholate cases are numbered 07 and 08 under
  `validation/cases/` and remain excluded from formal pass counts.
- The failed methane case was removed from the release validation set.
- Saved validation results contain no local Mac or Windows user path.
- Figure export is inactive unless the user explicitly supplies an output path;
  no CSV export is enabled.
- The exact saved Core-6 and Core-15 manuscript inputs and outputs are archived
  under `CANNEX_study/` with SHA-256 checksums and an AGORA2 third-party notice.
- Release clutter (`.DS_Store` and compiled Python caches) has been removed,
  and no personal computer path was found in the release text files.
- A short GitHub Actions workflow is configured for clean Python 3.11 tests on
  Linux and Windows. Its first remote run remains to be confirmed after upload.
- The public README now introduces the scientific purpose, inputs, six-stage
  workflow, installation, Excel output and separate validation tutorials.
- Cases 01-08 each have a supporting paper, a reproducible command, the locked
  Excel result and a short interpretation in `validation/README.md`.
- `CITATION.cff` records Khoi Nguyen as the software author. Repository URL,
  release date and DOI will be added when they exist.

## Small regression result that must still be relocked

The current generalized precursor search was rerun against the small five-GEM
regression panel and retained 78 unique edges: 42 for butyrate and 36 for GABA.
All ten edges in the older regression file remain present, but the current run
adds 68 alternative edges. This small regression panel is distinct from the
saved 29-GEM Core-6 and 37-GEM Core-15 manuscript analyses under
`CANNEX_study/`.

Do not silently discard the additional edges and do not update the expected
file only to make the test pass. First review the 78-edge result biologically,
then lock the accepted edge identities in
`config/expected_manuscript_edges.tsv`. Update the Windows full-analysis wording
and the R visualization regression counts at the same time.

## Items requiring author or institutional information

- Add the repository URL, release date and DOI to `CITATION.cff` when they
  exist.
- Confirm the final target-selection wording and cited references against the
  manuscript Methods section.
- Confirm institutional approval for the BSD-3-Clause license and the
  provisional `XiaLab` copyright holder.
- Complete a real Windows 10/11 test with the supplied launcher before public
  deposit; macOS checks cannot replace that operating-system test.

## Suggested release sequence

1. Review and lock the generalized manuscript edge set.
2. Rerun the full five-model regression and R visualization check.
3. Complete citation metadata and institutional ownership confirmation.
4. Run the Windows compatibility test.
5. Upload to GitHub and confirm the automated Linux/Windows checks.
6. Create the GitHub release or archival ZIP and record its permanent DOI.

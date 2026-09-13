# Manuscript software release checklist

Status checked on 2026-09-12. This checklist applies only to the scripts and
cross-feeding validation materials in this prototype.

## Completed technical checks

- Main Python entry point is `find_crossfeeding.py`; no computer-specific path
  is embedded in the scripts, saved JSON files or saved Excel workbooks.
- Dependencies are pinned consistently in `requirements.txt` and
  `environment.yml`.
- All 26 automated tests pass without skips.
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
  Windows, and the remote workflow passes.
- The public README now introduces the scientific purpose, inputs, six-stage
  workflow, installation, Excel output and separate validation tutorials.
- Cases 01-08 each have a supporting paper, a reproducible command, the locked
  Excel result and a short interpretation in `validation/README.md`.
- `CITATION.cff` records Khoi Nguyen as the software author and includes the
  public repository URL. Release date and DOI will be added when they exist.

## Items requiring author or institutional information

- Add the release date and DOI to `CITATION.cff` when they exist.
- Confirm the final target-selection wording and cited references against the
  manuscript Methods section.
- Confirm institutional approval for the BSD-3-Clause license and the
  provisional `XiaLab` copyright holder.
- Complete a real Windows 10/11 test with the supplied launcher before public
  deposit; macOS checks cannot replace that operating-system test.

## Suggested release sequence

1. Complete citation metadata and institutional ownership confirmation.
2. Run the supplied tutorial on a laboratory Windows 10/11 computer.
3. Confirm the automated Windows check after the final commit.
4. Create the GitHub release or archival ZIP and record its permanent DOI.

# Manuscript visualization reproduction

This directory reproduces the validation and pathway-network figures exactly
as they appear in the active CANNEX manuscript report. It is a separate,
study-specific presentation layer and is not part of the core Python
cross-feeding pipeline.

The visualization code does not discover, filter, or reclassify potential
edges. It reads locked tutorial and CANNEX analysis outputs and reproduces:

- Figure V1: validation outcome counts;
- Figure V2: validation Cases 01-02;
- Figure V3: validation Cases 03-04;
- Figure V4: validation Case 05;
- Figure V5: validation Cases 06-08;
- Figure F: combined Core-6/Core-15 GABA Case-2 network; and
- Figure G: combined Core-6/Core-15 butyrate Case-2 network.

The result is a self-contained HTML file. Each network also has buttons in the
HTML for downloading an SVG or PNG copy.

## Requirements

- R
- Pandoc (included with RStudio)
- R packages: `rmarkdown`, `knitr`, `DiagrammeR`, `digest`, `dplyr`,
  `ggplot2`, `ggalluvial`, `ggnewscale`, `htmltools`, `jsonlite`, `readxl`,
  `scales`, `kableExtra`, `stringr`, and `tidyr`

Install missing R packages once:

```r
install.packages(c(
  "rmarkdown", "knitr", "DiagrammeR", "digest", "dplyr", "ggplot2",
  "ggalluvial", "ggnewscale", "htmltools", "jsonlite", "readxl", "scales",
  "kableExtra", "stringr", "tidyr"
))
```

## Run

From any folder, run:

```bash
Rscript /path/to/target-guided-crossfeeding/visualization/render_visualizations.R
```

Alternatively, open `reproduce_manuscript_visualizations.Rmd` in RStudio and
select **Knit**. No path needs to be edited.

The rendered report is written to:

```text
visualization/outputs/CANNEX_manuscript_visualizations.html
```

## Locked inputs and source

- `source/CANNEX_CORE6_CORE15_CROSSFEEDING_SUMMARY.Rmd` is the copied active
  manuscript Rmd and is the authoritative source for the figure-building code,
  figure text, parameters, and scientific rules.
- `inputs/gem_screening/` contains the six locked Core-6/Core-15 files needed
  by the two pathway networks.
- `../validation/VALIDATION_INDEX.tsv` and
  `../validation/validation_summary.csv` provide the locked validation-case
  results.
- `inputs/SHA256SUMS` records the checksums of the copied CANNEX inputs. The
  manuscript code also checks its expected input hashes before plotting.

The full manuscript Rmd is retained for traceability. The shorter
`reproduce_manuscript_visualizations.Rmd` evaluates only the exact chunks
needed for the seven figures listed above.

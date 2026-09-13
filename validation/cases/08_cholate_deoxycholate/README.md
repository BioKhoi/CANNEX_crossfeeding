# Cholate-to-deoxycholate case: partly supported

## Literature route

*Bacteroides thetaiotaomicron* VPI-5482 -> cholate ->
*Clostridium scindens* ATCC 35704 -> deoxycholate.

This is a mechanistically composed exact-strain case: the references support
the relevant function of each strain, but not a direct co-culture validation of
this exact pair. The analysis was target-only and did not supply cholate or the
organism roles to the discovery workflow.

## Result

- Potential cross-feeding edges retained: **2** (formate and L-glutamate).
- The recipient passed deoxycholate production, transport and export screening.
- Cholate was independently discovered as a recipient precursor.
- The expected cholate edge was excluded because the donor GEM could not
  independently produce cholate.

The formate and L-glutamate edges do not confirm the literature mechanism and
must not be counted as validation of the expected route. This case is not a
validation pass.

The source *B. thetaiotaomicron* XML contained one invalid legacy annotation
byte unrelated to this pathway; the copy here was converted to valid UTF-8
without changing the source file.

## References

- Yao L, et al. eLife. 2018;7:e37182. doi:10.7554/eLife.37182
- Devendran S, et al. Applied and Environmental Microbiology. 2019;85:e00052-19.
  doi:10.1128/AEM.00052-19
- Karcher N, et al. Nature Communications. 2024.
  doi:10.1038/s41467-024-48543-3

## Rerun from the prototype root

```bash
.venv/bin/python create_model_manifest.py \
  --gem-dir validation/cases/08_cholate_deoxycholate/models \
  --output validation/cases/08_cholate_deoxycholate/config/model_manifest.tsv

.venv/bin/python find_crossfeeding.py \
  --gem-dir validation/cases/08_cholate_deoxycholate/models \
  --targets validation/cases/08_cholate_deoxycholate/config/targets.tsv \
  --output validation/cases/08_cholate_deoxycholate/results/result.xlsx
```

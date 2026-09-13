# Indole-3-lactate-to-IPA case: partly supported

## Literature route

*Lactobacillus reuteri* I5007 -> indole-3-lactate ->
*Clostridium sporogenes* ATCC 15579 -> indole-3-propionate (IPA).

The analysis was target-only: IPA was supplied as the target, without providing
the expected precursor or organism roles to the discovery workflow.

## Result

- Potential cross-feeding edges retained: **8**.
- The recipient passed IPA production, transport and export screening.
- The retained alternative precursors were acetaldehyde, L-alanine, ethanol,
  L-glutamate, glycerol, glycerol-3-phosphate, D-lactate and L-lactate.
- The expected indole-3-lactate edge was not recovered.
- The *L. reuteri* I5007 GEM does not contain indole-3-lactate.

The eight alternative edges are structural hypotheses and do not validate the
published indole-3-lactate route. The expected intermediate cannot be tested by
this exact donor GEM, so this case is not a validation pass.

## Reference

- Wang G, et al. Microbiome. 2024;12:59.
  doi:10.1186/s40168-024-01750-y

## Rerun from the prototype root

```bash
.venv/bin/python create_model_manifest.py \
  --gem-dir validation/cases/07_indole_lactate_ipa/models \
  --output validation/cases/07_indole_lactate_ipa/config/model_manifest.tsv

.venv/bin/python find_crossfeeding.py \
  --gem-dir validation/cases/07_indole_lactate_ipa/models \
  --targets validation/cases/07_indole_lactate_ipa/config/targets.tsv \
  --output validation/cases/07_indole_lactate_ipa/results/result.xlsx
```

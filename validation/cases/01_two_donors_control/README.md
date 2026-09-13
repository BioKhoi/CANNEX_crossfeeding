# Case 1: two donors and one consumer

This three-strain panel holds L-lactate, the consumer, butyrate, diet and
workflow settings fixed while changing only the donor.

```text
Positive: Bifidobacterium adolescentis L2-32 -> L-lactate
          -> Eubacterium hallii L2-7 -> butyrate

Negative: Paraprevotella xylaniphila YIT 11841 -X-> L-lactate
          -> the same E. hallii L2-7 -> butyrate
```

Belenguer et al. directly tested the exact positive strains in coculture and
traced lactate carbon into butyrate. Morotomi et al. characterized the exact
YIT 11841 type strain as producing succinate and acetate, rather than lactate,
as glucose-fermentation end products.

Primary references:

1. Belenguer A, et al. AEM. 2006;72:3593-3599.
   https://doi.org/10.1128/AEM.72.5.3593-3599.2006
2. Morotomi M, et al. IJSEM. 2009;59:1895-1900.
   https://doi.org/10.1099/ijs.0.008169-0

Run from the project root:

```bash
python find_crossfeeding.py \
  --gem-dir validation/cases/01_two_donors_control/models \
  --targets validation/cases/01_two_donors_control/config/targets.tsv \
  --output validation/cases/01_two_donors_control/results/case1_two_donors_lactate_butyrate.xlsx
```

## Verified result

- L2-32 donor edge: **retained**. Intracellular L-lactate formation, outward
  transport and exchange export all passed.
- YIT 11841 donor edge: **excluded**. No target-withheld intracellular
  L-lactate production path was retained, and no outward L-lactate supply was
  available.
- Exactly one of the two tested donor edges was retained.

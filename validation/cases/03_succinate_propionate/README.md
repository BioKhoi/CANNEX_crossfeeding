# Positive control: succinate-supported propionate formation

This validation case uses the exact strains tested in the primary co-culture
study:

```text
Paraprevotella xylaniphila YIT 11841
    -> succinate
Phascolarctobacterium succinatutens YIT 12067
    -> propionate
```

Watanabe et al. reported that YIT 12067 grew in xylan-containing co-culture
with the succinate-producing YIT 11841 strain, succinate became undetectable,
and propionate was formed (Applied and Environmental Microbiology, 2012,
doi:10.1128/AEM.06035-11).

Run from the project root:

```bash
python find_crossfeeding.py \
  --gem-dir validation/cases/03_succinate_propionate/models \
  --targets validation/cases/03_succinate_propionate/config/targets.tsv \
  --output validation/cases/03_succinate_propionate/results/positive_succinate_propionate.xlsx
```

The 2026-08-30 run retained one GEM-supported potential edge under the bundled
HighFiber AGORA2 anaerobic condition. This qualitative result supports pathway
compatibility with the experimental observation; it does not independently
prove secretion amount, metabolite transfer, or growth benefit.

Confirm AGORA2 redistribution terms before publishing the XML working copies.

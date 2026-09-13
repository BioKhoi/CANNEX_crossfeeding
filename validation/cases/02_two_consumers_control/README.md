# Case 2: one donor and two consumers

This three-strain panel holds the L-lactate donor, precursor, butyrate, diet and
workflow settings fixed while changing only the consumer.

```text
Positive: Bifidobacterium adolescentis L2-32 -> L-lactate
          -> Eubacterium hallii L2-7 -> butyrate

Negative: the same B. adolescentis L2-32 -> L-lactate
          -X-> Phascolarctobacterium succinatutens YIT 12067 -> butyrate
```

The exact L2-7 strain uses both D- and L-lactate and forms butyrate. The exact
YIT 12067 strain was tested against lactate but used only succinate, which it
converted to propionate. This supports an expected absent lactate-to-butyrate
consumer edge.

Primary references:

1. Duncan SH, et al. AEM. 2004;70:5810-5817.
   https://doi.org/10.1128/AEM.70.10.5810-5817.2004
2. Belenguer A, et al. AEM. 2006;72:3593-3599.
   https://doi.org/10.1128/AEM.72.5.3593-3599.2006
3. Watanabe Y, et al. AEM. 2012;78:511-518.
   https://doi.org/10.1128/AEM.06035-11

Run from the project root:

```bash
python find_crossfeeding.py \
  --gem-dir validation/cases/02_two_consumers_control/models \
  --targets validation/cases/02_two_consumers_control/config/targets.tsv \
  --output validation/cases/02_two_consumers_control/results/case2_two_consumers_lactate_butyrate.xlsx
```

The `Consumer Audits` worksheet explicitly records why the negative consumer
was excluded instead of silently dropping the absent edge.

## Verified result

- L2-7 consumer: **retained**. L-lactate import, the expected
  L-lactate-to-butyrate route, target transport and butyrate export all passed.
- YIT 12067 consumer: **excluded**. The GEM lacks L-lactate exchange import and
  inward transport and has no L-lactate-to-butyrate route.
- Exactly one of the two tested consumers passed.

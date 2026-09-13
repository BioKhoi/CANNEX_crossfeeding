# Retained partial control: putrescine pathway

The experimentally established exact-strain route is:

```text
environmental arginine
    -> Streptococcus gordonii DL1/Challis
    -> ornithine
    -> Fusobacterium nucleatum ATCC 25586
    -> putrescine
```

Sakanaka et al. demonstrated ArcD-dependent ornithine release by *S. gordonii*
and ornithine-dependent putrescine formation by *F. nucleatum* (mSystems 2022,
doi:10.1128/msystems.00170-22; JBC 2015,
doi:10.1074/jbc.M115.644401).

## Unbiased computational result

The discovery input supplied putrescine as the target but did not supply the
expected precursor or organism roles. The workflow retained an
arginine-to-ornithine-to-putrescine path in the *F. nucleatum* reconstruction:

```text
arginine -> ornithine -> putrescine
```

It did not recover extracellular ornithine as the exchanged root. The GEM
contains outer-membrane ornithine movement, but its inner-membrane movement is
coupled to an arginine/ornithine antiporter. It also contains a low-confidence
arginase reaction that newer biochemical evidence does not support for this
strain (Mothersole et al. 2022, doi:10.1021/acs.biochem.2c00197).

The result is therefore retained as a **partial pathway match**:

- putrescine-production potential was recovered;
- the arginine-ornithine-putrescine biochemical axis was partially recovered;
- the exact donor-ornithine-recipient edge was not reproduced.

It must not be described as an exact validation of the exchanged metabolite.

Run from the project root:

```bash
python find_crossfeeding.py \
  --gem-dir validation/cases/06_putrescine_partial/models \
  --targets validation/cases/06_putrescine_partial/config/targets.tsv \
  --output validation/cases/06_putrescine_partial/results/result.xlsx
```

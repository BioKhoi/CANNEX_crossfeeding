# Literature-positive lactate-to-hydrogen-sulfide control

```text
Bifidobacterium adolescentis L2-32
    -> L-lactate
Desulfovibrio piger DSM 749 / ATCC 29098
    -> hydrogen sulfide
```

Marquet et al. directly tested these exact biological strains and found that
the lactate-producing *B. adolescentis* L2-32 stimulated sulfide formation by
*D. piger* DSM 749 in sulfate-containing coculture (FEMS Microbiology Letters,
2009, doi:10.1111/j.1574-6968.2009.01750.x). DSMZ identifies DSM 749 and ATCC
29098 as the same *D. piger* type strain.

## Computational result

The discovery input contained the target `h2s` but did not contain the expected
precursor or expected organism roles. The bounded alternative-path search
independently nominated `lac_L`, and donor screening retained the expected
GEM-supported potential edge:

```text
B. adolescentis L2-32 -> L-lactate -> D. piger ATCC 29098 -> H2S
```

The donor reconstruction forms L-lactate through `LDH_L`, transports it
outward through `L_LACt2r`, and permits exchange export. Retained recipient
paths include periplasm-aware L-lactate uptake and `LDH_L`-supported reducing
power for H2S formation.

```text
lac_L[e] -> lac_L[p] -> lac_L[c]
lac_L[c] + NAD -> pyruvate + NADH
sulfite + NADH -> H2S
H2S[c] -> H2S[p] -> H2S[e]
```

The search also nominated other GEM-supported extracellular roots and retained
six donor-to-recipient candidate edges in this two-model panel. Some H2S paths
require several roots (for example, an electron donor plus a sulfur source), so
the result records complete path-root sets and must not be read as proof that
each precursor is sufficient alone. The literature lactate edge is the held-out
validation relation; the other predictions are not automatically biological
positives.

This is a qualitative, non-flux result. It supports encoded metabolic
potential under the selected environment; it does not quantify sulfide flux
or establish realized cross-feeding in a new experiment.

Files:

- `models/`: exact-strain AGORA2 working copies.
- `config/model_manifest.tsv`: generated checksums and SBML metadata.
- `config/targets.tsv`: H2S target only; it contains no expected precursor or
  expected organism role.
- `results/result.xlsx` and `results/result.json`: complete results and
  reaction-level evidence.

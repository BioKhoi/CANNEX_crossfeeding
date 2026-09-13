# Positive control: NCC2705 to ATCC 33656

```text
Bifidobacterium longum NCC2705
    -> acetate
Eubacterium rectale ATCC 33656
    -> butyrate
```

Riviere et al. directly tested these exact strains on arabinoxylan
oligosaccharides and reported that donor-produced acetate supported butyrate
formation by the recipient (Applied and Environmental Microbiology, 2015,
doi:10.1128/AEM.02089-15).

Run from the project root:

```bash
python find_crossfeeding.py \
  --gem-dir validation/cases/04_acetate_butyrate/models \
  --targets validation/cases/04_acetate_butyrate/config/targets.tsv \
  --output validation/cases/04_acetate_butyrate/results/result.xlsx
```

Confirm AGORA2 redistribution terms before publishing the XML working copies.

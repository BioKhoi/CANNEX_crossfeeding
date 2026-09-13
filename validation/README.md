# Validation tutorials: Cases 01-08

These tutorials demonstrate how to run the pipeline and interpret its Excel
potential-edge output. The papers define held-out biological expectations;
the expected precursor, donor, recipient and answer are not supplied to the
discovery workflow.

Run every command from the repository root after activating the environment.
Write new results under `outputs/` so the locked workbooks under each case's
`results/` folder are not overwritten.

The eight cases have different evidential roles:

- Cases 01 and 02 are matched positive/negative controls.
- Cases 03-05 are exact-strain positive validation examples.
- Case 06 is a partial pathway match.
- Cases 07 and 08 are boundary examples in which the expected biological
  route is incompletely represented by the selected GEMs.

## Case 01: two donors and one recipient

**Relationship tested:** *Bifidobacterium adolescentis* L2-32 supplies
L-lactate to *Eubacterium hallii* L2-7 for butyrate production, whereas
*Paraprevotella xylaniphila* YIT 11841 is the negative donor.

**Papers:** Belenguer et al. (2006),
[doi:10.1128/AEM.72.5.3593-3599.2006](https://doi.org/10.1128/AEM.72.5.3593-3599.2006);
Morotomi et al. (2009),
[doi:10.1099/ijs.0.008169-0](https://doi.org/10.1099/ijs.0.008169-0).

```bash
python find_crossfeeding.py --gem-dir validation/cases/01_two_donors_control/models --targets validation/cases/01_two_donors_control/config/targets.tsv --check-only
python find_crossfeeding.py --gem-dir validation/cases/01_two_donors_control/models --targets validation/cases/01_two_donors_control/config/targets.tsv --output outputs/case01.xlsx
```

**Excel result:** seven potential edges were retained overall. Within the
prespecified L-lactate comparison, the L2-32 donor edge was retained and the
YIT 11841 donor edge was excluded.

**Interpretation:** The pipeline separated the literature-supported positive
donor from the biological negative donor while holding the recipient,
precursor and target constant.

## Case 02: one donor and two recipients

**Relationship tested:** *B. adolescentis* L2-32 supplies L-lactate to the
positive *E. hallii* L2-7 recipient or the negative
*Phascolarctobacterium succinatutens* YIT 12067 recipient for butyrate
production.

**Papers:** Duncan et al. (2004),
[doi:10.1128/AEM.70.10.5810-5817.2004](https://doi.org/10.1128/AEM.70.10.5810-5817.2004);
Belenguer et al. (2006),
[doi:10.1128/AEM.72.5.3593-3599.2006](https://doi.org/10.1128/AEM.72.5.3593-3599.2006);
Watanabe et al. (2012),
[doi:10.1128/AEM.06035-11](https://doi.org/10.1128/AEM.06035-11).

```bash
python find_crossfeeding.py --gem-dir validation/cases/02_two_consumers_control/models --targets validation/cases/02_two_consumers_control/config/targets.tsv --check-only
python find_crossfeeding.py --gem-dir validation/cases/02_two_consumers_control/models --targets validation/cases/02_two_consumers_control/config/targets.tsv --output outputs/case02.xlsx
```

**Excel result:** seven potential edges were retained overall. Within the
prespecified L-lactate comparison, the L2-7 recipient edge was retained; the
YIT 12067 edge was excluded because the GEM lacked L-lactate import and a
retained L-lactate-to-butyrate route.

**Interpretation:** The matched design shows that donor production alone is
insufficient; the recipient must also encode compatible precursor uptake and
target production.

## Case 03: succinate to propionate

**Relationship tested:** *P. xylaniphila* YIT 11841 supplies succinate to
*P. succinatutens* YIT 12067 for propionate production.

**Paper:** Watanabe et al. (2012),
[doi:10.1128/AEM.06035-11](https://doi.org/10.1128/AEM.06035-11).

```bash
python find_crossfeeding.py --gem-dir validation/cases/03_succinate_propionate/models --targets validation/cases/03_succinate_propionate/config/targets.tsv --check-only
python find_crossfeeding.py --gem-dir validation/cases/03_succinate_propionate/models --targets validation/cases/03_succinate_propionate/config/targets.tsv --output outputs/case03.xlsx
```

**Excel result:** one potential edge was retained, corresponding to the exact
succinate-supported propionate relationship.

**Interpretation:** The predicted structural relationship agrees with the
exact-strain coculture observation reported in the paper.

## Case 04: acetate to butyrate

**Relationship tested:** *Bifidobacterium longum* NCC2705 supplies acetate to
*Eubacterium rectale* ATCC 33656 for butyrate production.

**Paper:** Riviere et al. (2015),
[doi:10.1128/AEM.02089-15](https://doi.org/10.1128/AEM.02089-15).

```bash
python find_crossfeeding.py --gem-dir validation/cases/04_acetate_butyrate/models --targets validation/cases/04_acetate_butyrate/config/targets.tsv --check-only
python find_crossfeeding.py --gem-dir validation/cases/04_acetate_butyrate/models --targets validation/cases/04_acetate_butyrate/config/targets.tsv --output outputs/case04.xlsx
```

**Excel result:** ten potential edges were retained overall, including the
exact acetate-supported butyrate relationship.

**Interpretation:** The predicted potential edge is consistent with the
experimentally tested exact-strain relationship.

## Case 05: L-lactate to hydrogen sulfide

**Relationship tested:** *B. adolescentis* L2-32 supplies L-lactate to
*Desulfovibrio piger* DSM 749/ATCC 29098 for hydrogen-sulfide production.

**Paper:** Marquet et al. (2009),
[doi:10.1111/j.1574-6968.2009.01750.x](https://doi.org/10.1111/j.1574-6968.2009.01750.x).

```bash
python find_crossfeeding.py --gem-dir validation/cases/05_lactate_h2s/models --targets validation/cases/05_lactate_h2s/config/targets.tsv --check-only
python find_crossfeeding.py --gem-dir validation/cases/05_lactate_h2s/models --targets validation/cases/05_lactate_h2s/config/targets.tsv --output outputs/case05.xlsx
```

**Excel result:** six potential edges were retained overall, including the
expected L-lactate donor-recipient relationship.

**Interpretation:** The pipeline independently recovered the expected
precursor route from a target-only search, consistent with the exact-strain
coculture study.

## Case 06: putrescine pathway

**Relationship tested:** *Streptococcus gordonii* CH1/DL1 supplies ornithine
to *Fusobacterium nucleatum* ATCC 25586 for putrescine production.

**Papers:** Sakanaka et al. (2022),
[doi:10.1128/msystems.00170-22](https://doi.org/10.1128/msystems.00170-22);
Sakanaka et al. (2015),
[doi:10.1074/jbc.M115.644401](https://doi.org/10.1074/jbc.M115.644401);
Mothersole et al. (2022),
[doi:10.1021/acs.biochem.2c00197](https://doi.org/10.1021/acs.biochem.2c00197).

```bash
python find_crossfeeding.py --gem-dir validation/cases/06_putrescine_partial/models --targets validation/cases/06_putrescine_partial/config/targets.tsv --check-only
python find_crossfeeding.py --gem-dir validation/cases/06_putrescine_partial/models --targets validation/cases/06_putrescine_partial/config/targets.tsv --output outputs/case06.xlsx
```

**Excel result:** four potential edges were retained. Putrescine-production
potential and an arginine-to-ornithine-to-putrescine route were recovered, but
extracellular ornithine was not retained as the exchanged precursor.

**Interpretation:** This is a partial biochemical match, not an exact
validation of the literature-described donor-ornithine-recipient edge.

## Case 07: indole-3-lactate to indole-3-propionate

**Relationship tested:** *Lactobacillus reuteri* I5007 supplies
indole-3-lactate to *Clostridium sporogenes* ATCC 15579 for
indole-3-propionate production.

**Paper:** Wang et al. (2024),
[doi:10.1186/s40168-024-01750-y](https://doi.org/10.1186/s40168-024-01750-y).

```bash
python find_crossfeeding.py --gem-dir validation/cases/07_indole_lactate_ipa/models --targets validation/cases/07_indole_lactate_ipa/config/targets.tsv --check-only
python find_crossfeeding.py --gem-dir validation/cases/07_indole_lactate_ipa/models --targets validation/cases/07_indole_lactate_ipa/config/targets.tsv --output outputs/case07.xlsx
```

**Excel result:** recipient indole-3-propionate production and eight
alternative potential edges were found, but the expected indole-3-lactate edge
was not recovered because that metabolite is absent from the selected donor
GEM.

**Interpretation:** The pipeline found alternative structural hypotheses, but
this selected GEM pair cannot reproduce the published intermediate and is not
an exact validation pass.

## Case 08: cholate to deoxycholate

**Relationship tested:** *Bacteroides thetaiotaomicron* VPI-5482 supplies
cholate to *Clostridium scindens* ATCC 35704 for deoxycholate production.

**Papers:** Yao et al. (2018),
[doi:10.7554/eLife.37182](https://doi.org/10.7554/eLife.37182);
Devendran et al. (2019),
[doi:10.1128/AEM.00052-19](https://doi.org/10.1128/AEM.00052-19);
Karcher et al. (2024),
[doi:10.1038/s41467-024-48543-3](https://doi.org/10.1038/s41467-024-48543-3).

```bash
python find_crossfeeding.py --gem-dir validation/cases/08_cholate_deoxycholate/models --targets validation/cases/08_cholate_deoxycholate/config/targets.tsv --check-only
python find_crossfeeding.py --gem-dir validation/cases/08_cholate_deoxycholate/models --targets validation/cases/08_cholate_deoxycholate/config/targets.tsv --output outputs/case08.xlsx
```

**Excel result:** recipient deoxycholate production and cholate precursor
identification passed, but the donor GEM did not independently produce and
export cholate. Two unrelated alternative potential edges were retained.

**Interpretation:** The recipient portion of the mechanism is represented, but
the expected donor supply is absent; therefore this is a boundary example, not
an exact validation pass.

## Summary of locked comparisons

Seven prespecified comparisons are formally checked: the positive and negative
branches of Cases 01 and 02, plus Cases 03-05. All seven match their held-out
expectations. Cases 06-08 document partial or incomplete GEM representation
and are not counted as exact validation passes.

To check the distributed locked workbooks:

```bash
python validate_expected_cases.py
```

The Excel results are qualitative GEM-supported potentials. They do not prove
secretion amount, physical metabolite transfer, community flux, recipient
growth benefit or in vivo causality.

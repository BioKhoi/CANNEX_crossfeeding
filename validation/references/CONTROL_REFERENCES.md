# References for the retained validation set

This file distinguishes exact biological validation from GEM-supported
structural potential. All computational results remain qualitative.

## Matched lactate-to-butyrate triads

Positive route: *Bifidobacterium adolescentis* L2-32 -> L-lactate ->
*Eubacterium hallii* L2-7 -> butyrate.

- Belenguer A, et al. AEM. 2006;72:3593-3599.
  https://doi.org/10.1128/AEM.72.5.3593-3599.2006
- Duncan SH, et al. AEM. 2004;70:5810-5817.
  https://doi.org/10.1128/AEM.70.10.5810-5817.2004

Case 1 negative donor: *Paraprevotella xylaniphila* YIT 11841 was described as
producing succinate and acetate rather than lactate as glucose-fermentation end
products.

- Morotomi M, et al. IJSEM. 2009;59:1895-1900.
  https://doi.org/10.1099/ijs.0.008169-0

Case 2 negative consumer: *Phascolarctobacterium succinatutens* YIT 12067 used
succinate rather than tested lactate and converted succinate to propionate.

- Watanabe Y, et al. AEM. 2012;78:511-518.
  https://doi.org/10.1128/AEM.06035-11

## Pairwise succinate-to-propionate anchor

*P. xylaniphila* YIT 11841 -> succinate -> *P. succinatutens* YIT 12067 ->
propionate.

- Watanabe Y, et al. AEM. 2012;78:511-518.
  https://doi.org/10.1128/AEM.06035-11

## Pairwise acetate-to-butyrate anchor

*Bifidobacterium longum* NCC2705 -> acetate -> *Eubacterium rectale* ATCC
33656 -> butyrate.

- Riviere A, et al. AEM. 2015;81:7767-7781.
  https://doi.org/10.1128/AEM.02089-15

## Lactate-to-hydrogen-sulfide anchor

*B. adolescentis* L2-32 -> L-lactate -> *Desulfovibrio piger* DSM 749/ATCC
29098 -> H2S.

- Marquet P, et al. FEMS Microbiology Letters. 2009;299:128-134.
  https://doi.org/10.1111/j.1574-6968.2009.01750.x

## Retained partial putrescine pathway

The experiments support environmental arginine -> *S. gordonii* -> ornithine
-> *F. nucleatum* ATCC 25586 -> putrescine. The workflow recovered
putrescine-production potential and an arginine-linked route but not the exact
exchanged ornithine edge.

- Sakanaka A, et al. mSystems. 2022;7:e00170-22.
  https://doi.org/10.1128/msystems.00170-22
- Sakanaka A, et al. Journal of Biological Chemistry. 2015;290:21185-21198.
  https://doi.org/10.1074/jbc.M115.644401
- Mothersole RG, et al. Biochemistry. 2022;61:1378-1391.
  https://doi.org/10.1021/acs.biochem.2c00197

## Partly supported cases (not formal validation passes)

### Indole-3-lactate-to-indole-3-propionate

The exact-strain experiment supports *L. reuteri* I5007-derived
indole-3-lactate increasing IPA production by *C. sporogenes* ATCC 15579. The
expected edge could not be tested because the donor GEM lacks the intermediate.

- Wang G, et al. Microbiome. 2024;12:59.
  https://doi.org/10.1186/s40168-024-01750-y

### Cholate-to-deoxycholate

The evidence is mechanistically composed from exact-strain functions rather
than a direct co-culture study of this exact pair: *B. thetaiotaomicron*
VPI-5482 has relevant bile-salt-hydrolase evidence, and *C. scindens* ATCC
35704 converts cholate to deoxycholate. The workflow discovered cholate as a
recipient precursor but did not retain donor cholate production.

- Yao L, et al. eLife. 2018;7:e37182.
  https://doi.org/10.7554/eLife.37182
- Devendran S, et al. Applied and Environmental Microbiology. 2019;85:e00052-19.
  https://doi.org/10.1128/AEM.00052-19
- Karcher N, et al. Nature Communications. 2024.
  https://doi.org/10.1038/s41467-024-48543-3

# Method definition

## Scope

This workflow tests a target-focused hypothesis:

```text
donor bacterium -> precursor -> recipient bacterium -> selected target metabolite
```

The target metabolites are defined by the user before GEM analysis from
literature relevant to the host question. In the current study, GABA and butyrate are the
configured targets. The method is not an all-metabolite or all-pair discovery
screen.

## Step 1: user-selected target metabolites

For target `T`:

```text
Selected(T) = host relevance documented
              AND microbial evidence documented
              AND GEM identifier supplied
```

The Python validator records the rationale and reference, rejects duplicate or
incomplete target records, and reports whether the identifier occurs in the
supplied GEM set. A missing identifier is `Unresolved`, not biological evidence
that the organism cannot produce the metabolite.

## Step 2: target exchange export

For GEM `G` and selected target `T`, retain the pair when an extracellular
boundary reaction for `T` permits the outward direction according to the FBC
bounds.

```text
Step2(G,T) = Selected(T) AND ExchangeExport(G,T_e)
```

Exchange capability alone does not establish intracellular synthesis.

## Step 3: target outward transport

Require cytosolic and extracellular forms of the target and an FBC-permitted
cytosol-to-extracellular transport direction. A direct reaction or a
directionally valid cytosol-to-periplasm-to-extracellular reaction chain is
accepted; every reaction in a multistep chain is reported as evidence.

```text
Step3(G,T) = Step2(G,T) AND TransportOut(G,T_c -> T_e)
```

## Step 4: target-withheld intracellular production

Every metabolite with an extracellular species and an import-capable exchange
in the focal GEM is initially available as a hypothetical precursor. Oxygen and
the focal target are withheld. The diet remains recorded as study context but
does not restrict precursor discovery, because a cross-fed metabolite may be
absent from the starting diet and supplied by another organism.

Selected cytosolic currency cofactors are bootstrapped to break Boolean cycles.
Oxidized redox carriers are included, but NADH, NADPH and FADH2 are not; a
candidate path must therefore contain a reaction source for the reducing power
it uses.

Each FBC-permitted intracellular reaction direction is converted to an
irreversible MeneTools rule. Exchange boundaries are not used as intracellular
production reactions. `mene path --min` obtains a cardinality-minimal reaction
set reaching the cytosolic target for the current precursor-seed state.

After a path is found, each non-currency extracellular root used by that path
is withheld in a child search. Repeating this operation finds representative
paths supported by different precursor roots without supplying a literature-
expected precursor. The search retains at most 25 paths and uses at most 200
MeneTools calls per model-target pair; truncation is recorded in the result.

Each qualitative path then undergoes a stoichiometric feasibility filter.
Every selected reaction must carry a positive weight, unavailable internal
metabolites cannot have negative net production, and the target must have
strictly positive net production. This removes target-consuming/target-
regenerating cycles that do not produce net target.

```text
Step4(G,T) = Step3(G,T)
             AND at least one target-withheld path is found
             AND the path contains intracellular formation of T_c
             AND net production of T_c is positive
```

Non-currency extracellular roots of every retained path are nominated as
precursor candidates. A path may require more than one root; the path ID and
complete root set are retained so a single edge is not mistaken for a claim
that its precursor is sufficient by itself.

`--min` minimizes the number of selected reactions. It is not a shortest
sequence, flux, yield, growth, or biological-preference optimum.

MeneTools may contain several equally cardinality-minimal solutions while
returning one `one_path` for each search state. The main runner starts every
scientific stage with `PYTHONHASHSEED=0` and the environment pins MeneTools and
Clingo versions. This fixes the computational ordering for reproducibility; it
does not imply that a retained path is biologically preferred.

## Step 5: recipient precursor import

For recipient `R`, target `T`, and nominated precursor `P`:

```text
Step5(R,T,P) = Step4(R,T)
               AND ExchangeImport(R,P_e)
               AND TransportIn(R,P_e -> P_c)
```

This establishes structural import capability; it does not establish donor
availability or recipient benefit.

## Step 6: cross-species precursor donor

Species identity is read from the explicit model manifest. Same-species,
different-strain pairs are excluded under the current study rule.

The precursor is withheld from donor seeds. A donor passes when the precursor
is qualitatively reachable through a selected path containing intracellular
formation and the donor has outward transport and export capability.

```text
DonorPass(D,P) = Produce(D,P_c)
                 AND TransportOut(D,P_c -> P_e)
                 AND ExchangeExport(D,P_e)

Candidate(D,R,T,P) = Step5(R,T,P)
                     AND Species(D) != Species(R)
                     AND DonorPass(D,P)
```

The retained record is a potential cross-species precursor-supply edge.

## Evidence retained

The final JSON and workbook retain:

- target-selection rationale and reference;
- model, species, strain, and checksum provenance;
- target exchange and outward-transport evidence;
- target-withheld recipient production reactions;
- alternative path IDs, complete precursor-root sets, net-target checks, and
  search-truncation status;
- nominated precursor import and inward-transport evidence;
- target-withheld donor production reactions;
- donor outward-transport and exchange-export evidence.

## Limitations

1. MeneTools reachability is qualitative. The path-level net-production filter
   checks stoichiometric feasibility but does not optimize flux, growth, yield,
   or community benefit.
2. The bounded search records representative precursor-root alternatives, not
   every mathematically possible path. A reported truncation means additional
   routes may exist.
3. Hypothetical extracellular precursor availability and cofactor bootstrapping
   are explicit modeling assumptions.
4. A GEM can contain erroneous, incomplete, or permissive reactions.
5. Structural export and import capability do not prove metabolite secretion,
   transfer, consumption, growth benefit, or host causality.
6. Some retained paths require several extracellular roots. A donor edge for
   one root does not establish that this root is sufficient alone.
7. Results apply to the exact GEMs, identifiers, bounds, target table, and
   workflow version recorded in the release.

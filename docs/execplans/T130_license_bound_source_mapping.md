# T130: Licence-bound cross-study protein-corona mapping precheck

## Purpose

Resolve a specific gap exposed while searching for a T129 target: a public
mass-spectrometry deposit may be CC0 while the paper that explains its
material/size map is governed by different reuse terms.  T130 determines
whether such a map is public-redistributable, analysis-only, or not available
in a reusable source.  It is a source-policy and data-provenance task, not a
model run.

## Non-negotiable boundary

T129's CC0-only cohort is unchanged.  No author label, article figure,
supplementary table, or descriptive text becomes a model feature merely
because it appears to explain a PRIDE file name.  In particular, an
analysis-only map must remain outside the public release and cannot clear the
T129 CC0 admission gate.

The project-wide source policy separately recognises CC BY as
public-redistributable and CC BY-NC as analysis-only.  That general policy
does not override the narrower T129 CC0 cohort rule.  A future policy change
would require an explicit, versioned decision and a clean separation of any
restricted source-derived artefacts.

## Evidence screened

| Route | Verified source facts | Mapping status | Current decision |
| --- | --- | --- | --- |
| PRIDE `PXD052701` plus RSC DOI `10.1039/D4NA00345D` | The PRIDE release is anonymous-public CC0 and contains ten source-named MSF results `LF1-L` through `LF5-S`.  The RSC paper identifies the same accession, states that `LF-L` and `LF-S` arise from 200 nm and 100 nm extrusion filters, respectively, and documents five liposome formulations.  The article is CC BY-NC 3.0. | The scientific map is explicit, but its mapping source is analysis-only relative to a public package. | `ANALYSIS_ONLY_NONPUBLIC_MAPPING`; not admitted to the CC0 cohort.  It is one laboratory and cannot by itself establish a cross-study target. |
| PRIDE `PXD017776` | The PRIDE release is anonymous-public CC0 and has twelve source-named replicate result files.  Its official project protocol says that different molar ratios were used, but refers exact compositions to a supplementary table rather than providing a numeric file-to-condition map in the deposit. | No official CC0 numeric material map joins every named result file to a source-defined composition. | `NOT_ADMITTED_NUMERIC_MAP_UNAVAILABLE`.  Do not infer ratios from `dopc`, `dopcg`, `dopg`, or replicate tokens in file names. |
| RSC DOI `10.1039/C9NR08186K` | The independent Helsinki study is CC BY 3.0.  The official article lists four XLSX supplements (replicate biophysical calculations and three protein-result tables), but the supporting PDF says raw proteomics/MaxQuant output is available only on reasonable request.  Direct automated access from KAUST encounters a Cloudflare challenge. | Potentially public-redistributable article-level data, but neither the XLSX schema nor a shared source-level endpoint has yet been verified. | `REASSESSABLE_AFTER_MANUAL_DOWNLOAD`; it is not a target or external validation set. |

Sources inspected: official PRIDE project records
[`PXD052701`](https://www.ebi.ac.uk/pride/archive/projects/PXD052701) and
[`PXD017776`](https://www.ebi.ac.uk/pride/archive/projects/PXD017776), the
RSC article for [D4NA00345D](https://doi.org/10.1039/D4NA00345D), and the RSC
article for [C9NR08186K](https://doi.org/10.1039/C9NR08186K).  The conclusions
above are provenance decisions, not biological findings.

## Admission logic

```text
official unit -> explicit material/size map -> reusable licence
     -> source-defined protein endpoint -> second independent laboratory
     -> frozen shared preprocessing and split -> T121 amendment -> T123
```

Failure at any arrow yields a non-admission receipt.  A completed mapping
check is not model fitting, an ablation, OOD evaluation, independent
validation, scientific reproduction, or editorial acceptance.

## Work plan and exit criteria

1. Create a machine-verifiable source-map registry that carries the exact
   source locator, licence class, file/unit coverage, material fields and
   endpoint scale for each mapping claim.
2. Admit only mappings whose reuse class is compatible with the intended
   artefact.  A CC BY-NC source may be audited in controlled analysis storage
   only after an explicit sponsor policy decision; it must never leak into the
   public source bundle.
3. If a user completes the publisher's normal browser verification for
   `C9NR08186K`, download only the listed small supplements, checksum them,
   inspect workbook schema and decide whether they map source units to a
   common endpoint.  Do not bypass the challenge or substitute search snippets
   for the files.
4. Even if both maps close, require two independent laboratories, one
   source-defined endpoint and a frozen T121 amendment before any T123 model
   process begins.

## Current decision

`BLOCKED_NO_PUBLIC_CROSS_STUDY_NUMERIC_MATERIAL_TARGET`.

## Validation and completion

- [x] `python -m biointerfaceos model audit-license-bound-source-maps --strict`
  writes `reports/review_round_2/license_bound_source_maps/v1.0.0/`, then
  re-verifies the registry hash, all route decisions and the false
  target/model/submission fields.
- [x] Regression tests reject a non-CC0 relabelling of the analysis-only map
  and a tampered receipt.

T130 is complete at its source-policy boundary.  Its acceptance is a correct
and reproducible decision boundary, not a positive target.  The remaining
source acquisition and target-freeze work continues in T129; T124, T126--T128
and all empirical submission claims remain blocked.

# R4-T246 paper-data candidate screen: PMC9047655 biological context

Status: `NOT_ADMITTED_AS_PROTEIN_TARGET_MATRIX`

This candidate was downloaded and inspected because it reports eight healthy
donor plasma samples used to form silica nanoparticle coronas. The article is
openly licensed, but its public supplementary workbook is a glycan-analysis
workbook rather than a donor-by-protein quantitative protein-corona matrix.

## Verified assets

| Item | Value |
|---|---|
| Article | Nanoparticle Biomolecular Corona-Based Enrichment of Plasma Glycoproteins for N-Glycan Profiling and Application in Biomarker Discovery |
| DOI / PMCID | `10.1021/acsnano.1c09564` / `PMC9047655` |
| License | CC BY-4.0 |
| Primary article package | `https://pmc-oa-opendata.s3.amazonaws.com/PMC9047655.1/PMC9047655.1.pdf` |
| SI PDF | `nn1c09564_si_001.pdf`, SHA-256 `4D54DE813D48275C4E5B00CCD4671FE6C5C63DA45845E841D821F9A495E16CE7` |
| SI workbook | `nn1c09564_si_002.xlsx`, SHA-256 `3B305A361A02B242368D13FDA8C06281DC469BECB7D9C608B116066BA01B97A2` |
| SI workbook sheets | `Title`, `Table S1`--`Table S5` |

## Admission decision

The article text supports the biological context claim of eight donor plasma
samples, and the workbook contains glycan peak assignments and group-level
glycan statistics. It does not expose a row-traceable donor × protein
abundance table on the frozen UniProt target scale. The candidate is therefore
retained as supporting biological context only and is not merged into the
BioInterfaceOS protein target ledger or model endpoint.

This is a positive exclusion: it prevents a donor count from being converted
into protein effective `n` without the required source cells. It does not close
the independent-laboratory, protected lockbox, no-author reproduction or
adoption gates.

Primary source pages:

- `https://pmc.ncbi.nlm.nih.gov/articles/PMC9047655/`
- `https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC9047655`
- `https://pubs.acs.org/doi/10.1021/acsnano.1c09564`

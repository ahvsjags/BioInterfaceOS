# R2 operational glossary and comparability rules

This glossary is mandatory for the T126 A+B manuscript and the T127 Paper C
protocol. It defines data fields and comparison boundaries; it does not change
the original authors' terminology or manufacture missing metadata. The fields
follow the reporting and ontology concerns raised by MIRIBEL, MINBE and
eNanoMapper.

| Term | Operational definition | Required source record | Comparison rule |
|---|---|---|---|
| Material | The physical nano-object or formulated nanomaterial, including core/composition, surface modification, size descriptor and measurement method where reported. | Source material label; composition; size descriptor; size method; surface/coating; batch if available. | Do not treat nominal, TEM, DLS, or z-average size as interchangeable. Retain the source's definition and unit. |
| Biology | The biological system in which the interface is measured, including biofluid/medium, species, cell/tissue/organism and relevant preparation state. | Biological system; medium/biofluid; species/cell type; biological condition. | A change in biofluid, species, cell system or biological state defines a distinct biological context unless a pre-frozen harmonisation rule says otherwise. |
| Protocol | The experimental and analytical procedure that generated an observation: exposure, dose/concentration, incubation time, temperature, ionic composition, recovery/isolation, assay and processing. | Protocol identifier and description; exposure condition; time; dose/concentration; assay/method; preprocessing. | Do not pool observations across protocol differences merely because material labels match. Protocol is a potential shift/group key. |
| Outcome | The measured response supplied by the source, together with endpoint definition, value, uncertainty/replicate information when available and unit. | Endpoint identifier/name; source value/cell; source unit; uncertainty or absence; measurement method. | Only an identical endpoint definition and compatible unit can enter a common target. Undefined units, different constructs and different assays are not convertible by default. |
| Independent unit | The smallest source-defined experimental entity that can be sampled once for uncertainty or split accounting, such as an independent GUV, formulation-time-condition measurement or study-defined sample. | Source-defined label and raw locator(s). | Effective n counts unique independent units, not cells, repeated exports, seeds or rows derived from the same unit. |
| Evidence locator | A stable pointer to the original source evidence, currently raw asset checksum plus worksheet/table and cell/row locator. | Landing URL; DOI/accession; raw asset URL; SHA-256; bytes; worksheet/table; locator. | A locator verifies source resolution only. It does not verify a scientific claim or create a prediction target. |
| OOD group | A pre-declared natural shift group held out from fitting, such as study, laboratory, material family, biological context, protocol or time. | Frozen group key; source/study/laboratory IDs; overlap report; effective n. | An OOD claim requires a compatible target, a declared external cohort, no group leakage, overlap, effective n, calibration and uncertainty. One study per endpoint is insufficient. |

## Mandatory source and outcome rules

1. Preserve the original unit and the measurement method even when a normalised
   analysis field is added. Normalisation requires a documented conversion and
   must fail when the underlying construct differs.
2. `source_not_stated` is an explicit missing value, never an implicit common
   unit. It blocks cross-study outcome pooling.
3. A biological or protocol field may be absent from a source. Missingness must
   be represented as missing and reported in coverage, not guessed from a
   similar paper.
4. A model target may be frozen only after at least three independent studies
   and laboratories provide the same endpoint and unit with adequate source
   lineage. T123 applies this gate.
5. Human/experimental generalisation, biological mechanism and causal effects
   require evidence beyond a metadata glossary, source-cell audit or software
   replay.

## Source anchors

- Faria et al. 2018, MIRIBEL ? <https://doi.org/10.1038/s41565-018-0246-4>
- Chetwynd et al. 2019, MINBE ? <https://doi.org/10.1016/j.nantod.2019.06.004>
- Hastings et al. 2015, eNanoMapper ? <https://doi.org/10.1186/s13326-015-0005-5>
- Wilkinson et al. 2016, FAIR ? <https://doi.org/10.1038/sdata.2016.18>

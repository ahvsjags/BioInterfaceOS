# Specialized Nanodatabase Admission Audit

## Scope and decision rule

This audit covers specialized nanomaterial resources that could contribute material identity, physicochemical characterization, biological interaction, toxicity, exposure, or protocol context to BioInterfaceOS. Decisions are based on official public documentation reviewed on 2026-08-12.

The policy rule is conservative:

- ADMIT_PUBLIC_SUBSTITUTE: anonymous public metadata/export path and a usable license/provenance signal are available; the source may be queued within the declared schema scope.
- METADATA_ONLY: public discovery is documented, but record-level license, export, or endpoint reproducibility is incomplete; retain pointers and metadata only.
- QUARANTINE: a public landing page exists, but anonymous machine access, exportability, or redistribution evidence is insufficient.
- REJECT: the audited access path requires credentials or partner authorization.

No credentials were requested or used. No specialized database payloads were downloaded.

## Candidate decisions

| Candidate | Anonymous access | API/export | License signal | Schema relevance | Decision |
|---|---|---|---|---|---|
| NanoCommons Knowledge Base | Official guidance describes authenticated, partner-restricted access | REST API is described, but the audited live access path is not anonymous | Handbook CC-BY-4.0 does not establish dataset-level rights | High: characterization, transformation, omics, toxicity, exposure/fate | REJECT |
| eNanoMapper public database | Public data/search page and API route documented | REST API and JSON/XLSX/RDF-style export documented | Ontology CC-BY-3.0 documented; data-record licenses need per-record confirmation | High: characterization, biological and toxicological data | METADATA_ONLY |
| Nanomaterial-Biological Interactions Knowledgebase | Public landing page observed | No stable official API/export contract verified in the audited material | No explicit redistribution license found on the landing page | High: material properties, synthesis, interactions | QUARANTINE |
| nanoPharos | Public dataset access and API are described by project material | REST/API and CSV/XLSX/XML access described; direct contract needs fixture verification | Dataset licensing is part of the FAIR model but not uniform enough for blind admission | High: properties, biointeractions, adverse effects, exposure, descriptors | METADATA_ONLY |
| PubChem + ChEMBL | Already implemented anonymous public adapters | Official public JSON services | Existing source-policy signals and tests | Medium: chemical identity/ligand/property supplements | ADMIT_PUBLIC_SUBSTITUTE |
| Zenodo + Figshare + OSF public releases | Already implemented anonymous public metadata adapters | Official APIs expose DOI/release metadata and file pointers | Per-release license is captured and gated before fetch | Medium-high: supplementary data, code, provenance | ADMIT_PUBLIC_SUBSTITUTE |

## Evidence links

- NanoCommons KB and access model: https://nanocommons.github.io/user-handbook/data-management/data-resources/NanoCommons-KB/ and https://nanocommons.github.io/user-handbook/data-management/data-resources/NanoCommons-KB-manual/
- eNanoMapper public data/API and documentation: https://www.enanomapper.net/data and https://www.enanomapper.net/documentation
- NBI Knowledgebase public description: https://nbi.nacse.org/
- nanoPharos resource description: https://nanocommons.github.io/user-handbook/data-management/data-resources/NanoPharos/ and https://db.nanopharos.eu/
- PubChem PUG REST: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
- ChEMBL Web Services: https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services
- Zenodo API: https://developers.zenodo.org/
- Figshare API: https://docs.figshare.com/
- OSF API v2: https://developer.osf.io/

## Schema fit

The candidate fields were compared against the current BioInterfaceOS contracts:

- material identity: composition, coating/functionalization, size, shape, charge, surface descriptors;
- bioenvironment/protocol: species, fluid, route, dose/concentration, exposure time, temperature, assay and replicate context;
- outcomes: uptake, viability, complement, inflammation, coagulation, biodistribution and toxicity;
- provenance: persistent identifier, source record, publication/dataset link, release/date, license and evidence locator.

eNanoMapper, NBI and nanoPharos are relevant to the scientific axes, but their access/license decisions prevent direct binary promotion at this stage. PubChem/ChEMBL fill chemical identity and ligand fields only. Public repository mirrors are the preferred route for supplementary files because DOI, release, license and checksums can be audited per record.

## Follow-up actions

1. Keep NanoCommons out of anonymous ingest until an approved public route and dataset-level licenses are documented.
2. Add eNanoMapper and nanoPharos metadata-only discovery jobs only after endpoint fixtures and record-level license extraction are pinned.
3. Do not build an NBI adapter until an official export/API and redistribution statement are supplied.
4. Prefer public Zenodo/Figshare/OSF releases or official paper-linked files for redistributable supplements.
5. Preserve the audit fixture and report as the decision source; any admission change requires a new version and new evidence record.

## Validation artifacts

- tests/fixtures/nanodatabases/admission_decisions.json
- tests/test_nanodatabase_audit.py
- src/biointerfaceos/nanodatabase_audit.py
- biointerfaceos source audit-specialized

The audit is metadata-only and does not claim that any specialized database is exhaustive, current beyond the audit date, or legally unrestricted for every underlying record.

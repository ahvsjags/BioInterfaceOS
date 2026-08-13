# T142: First-party supplementary asset and licence audit

## Purpose

Turn the T140 article-level lead into an auditable intake checklist. The
primary pages name five supplementary files across the UCD and PNNL studies,
but page metadata is not a byte-level source release and does not grant CC0
reuse.

## Current decision

`BLOCKED_FIRST_PARTY_BYTES_LICENCE_UNIT_MAP_AND_SHARED_ENDPOINT_REQUIRED`.

The audit records the exact filenames, declared page sizes, first-party
locators, page-level access observations and reuse boundary. No supplementary
bytes are retained, no file is marked redistributable, and no target or model
use is enabled.

## Required closure evidence

1. Contributor- or scope-owner-supplied bytes with SHA-256 and byte counts.
2. Explicit reuse terms for each file, with a segregated analysis-only route
   when public redistribution is not permitted.
3. Source-file/result-unit-to-size/material maps for both studies.
4. A common endpoint and preprocessing contract that supports study-held-out
   evaluation before T121 is amended.

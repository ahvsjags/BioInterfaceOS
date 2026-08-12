# T132: PXD017052 complete publisher-attachment correction

## Purpose

Correct the scope of T131 without rewriting its immutable v1.0 receipt. The
publisher lists eight additional attachments (`MOESM4`--`MOESM11`). A bounded
read-only inspection located an apparent unit-to-particle table in
Supplementary Data 6 (`MOESM8`): its 3-NP section pairs the nine T131 result
unit identifiers with `SP-003-001`, `SP-007-002` and `SP-011-001`, plus source
replicate numbers. T132 must verify every remaining attachment's checksum and
the table's exact cells before it can supersede the broad negative inference.

## Strict acceptance conditions

1. Download only the eight named publisher files through normal HTTPS to
   protected raw storage and preserve bytes, SHA-256, MD5 and publisher ETag.
2. Verify that the `MOESM8` 3-NP section has the declared title and headers,
   that its nine file identifiers exactly equal T131's nine quantitative
   result/raw basenames, and that each maps exactly once to a declared SPION
   and replicate number.
3. Keep the physical particle records and result table provenance separate:
   the T131 material table remains the evidence for SPION attributes; the
   T132 table is evidence for unit identity only.
4. Record a complete CC-BY source route only if all joins are explicit. It
   remains outside the frozen CC0 cohort; no model, OOD, independent-validation
   or submission claim is enabled without an explicit cohort amendment, a
   second independent laboratory and a shared frozen endpoint.

## Non-goals

T132 does not infer a CC0 licence, merge author-level intensity values across
studies, reinterpret technical replicates as external validation, or replace
the required T121 amendment.

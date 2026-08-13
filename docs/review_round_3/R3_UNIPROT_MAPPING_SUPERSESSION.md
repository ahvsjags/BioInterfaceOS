# R3 UniProt mapping supersession

`bioif-r3-uniprot-human-mapping-v1.0.0` was a conservative discovery pass. It
did not recognise 10-character UniProt accessions such as `A0A024QZ42`, and it
stored request metadata but not the exact API response bytes. It is therefore
not admissible evidence for target freezing or model fitting.

Version `v1.0.1` expands parsing to valid 6- and 10-character UniProt
accessions and writes the exact TSV response for every batch alongside a
hash-verified request manifest. Only the `v1.0.1` receipt may enter the R3
protocol-amendment gate.

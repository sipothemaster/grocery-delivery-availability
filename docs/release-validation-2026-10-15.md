# Release validation — 15 October 2026

These checks validate version 0.1.0 in the environment used for the Co-op
workflow. Live results describe this observation only and are not a guarantee
of future retailer access or availability.

## Offline and packaging checks

- All 22 deterministic tests passed.
- Ruff source and test checks passed.
- The wheel and source distribution built successfully, and the wheel installed
  successfully in a clean environment.
- Citation metadata, package version, licence, and release contents passed the
  repository's release-metadata tests.

## Co-op live checks

The integrated adapter attached to one operator-opened Microsoft Edge session
and queried `LS2 9JT`, `E1 6HQ`, `HS7 5PZ`, and `HS8 5TX` at a two-second
interval. All four responses were HTTP 200, confirmed the requested postcode,
reported delivery coverage, and returned a delivery rather than collection
slot. The urban controls had a first-slot wait of about 25 minutes; the two
island controls returned next-day slots about 21.4 and 25.4 hours away.

An eight-cycle consistency test produced 32/32 successful HTTP 200 responses,
with no postcode mismatch, `Unknown`, access-control response, or service-type
misclassification. Each postcode retained the same first-slot start across all
eight observations. Disconnecting after each cycle did not close the Edge
session.

A live resume test first collected two controls and then requested all four.
The second run reused the two completed observations unchanged and issued only
the two missing queries. Four business-response files were retained for the
four actual requests.

## Interpretation and remaining limitation

The next-day island slots demonstrate why delivery coverage and observed wait
time must remain separate fields. The live run did not include a currently
known non-deliverable Co-op postcode, so the live `No` branch was not exercised;
that branch is covered by synthetic offline tests. Raw live responses and CSVs
remain in the ignored runtime directory and are not release artefacts.

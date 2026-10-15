# Live smoke test — 30 September 2026

This test used `E1 6HQ`, `LS2 9JT`, and `ZE1 0AA` from a Windows host in the
United Kingdom. Results describe that run only; retailer interfaces and access
controls can change.

| Retailer | Yes | No | Unknown | Result |
|---|---:|---:|---:|---|
| Amazon Fresh | 1 | 2 | 0 | Passed |
| Chop Chop | 2 | 1 | 0 | Passed |
| Co-op | 0 | 0 | 3 | Blocked by HTTP 403 |
| Iceland | 2 | 1 | 0 | Passed in headed Chrome |
| Morrisons | 2 | 1 | 0 | Passed with product-catalogue validation |
| Ocado | 2 | 1 | 0 | Passed |

Co-op rejected both headless and headed Chrome bootstrap requests through its
current access-control layer. A follow-up manual test on 1 October 2026 loaded
the storefront, but the page itself reported that Imperva blocked both
`/api/auth/session` and `/api/store/set?postcode=...`. The tool records this as
`Unknown`, not `No`, and no attempt was made to bypass the block. The adapter is
retained as reproducibility evidence for the workflow that returned valid
postcode-specific responses during the historical collection.

Iceland rejected the headless homepage bootstrap but completed all three checks
in headed Chrome. This environment therefore requires `--headed` for Iceland at
the time of testing.

For Morrisons, `ZE1 0AA` returned a deliverable address decision but an empty
postcode-selected product catalogue, so the final result was correctly `No`.
`E1 6HQ` and `LS2 9JT` each returned a non-cached catalogue and were `Yes`.

Live CSV outputs are diagnostic runtime artefacts and are intentionally ignored
by Git.

# Repository instructions

- This is the public, citable implementation of the grocery delivery
  availability tool.
- Do not copy or import code, data, fixtures, logs, browser profiles, cloud
  identifiers, or Git history from the earlier internal repository.
- Keep all runtime outputs outside version control. Only small synthetic test
  fixtures belong in this repository.
- Preserve the three delivery states exactly: `Yes`, `No`, and `Unknown`.
  Technical failures, blocks, rate limits, address mismatches, and unexpected
  schemas are `Unknown`, never `No`.
- A missing current slot is not automatically evidence of no geographic
  coverage.
- Do not bypass authentication, CAPTCHAs, or anti-bot controls. Use conservative
  pacing and stop when a retailer rejects automated requests.
- Default tests must be offline and deterministic. Live retailer checks are
  explicit, opt-in smoke tests.
- Read `docs/responsible-data-collection.md` before any live collection. Treat
  its stop conditions and single-process limitation as repository rules.
- Do not add concurrency, multiple browser contexts, cloud fan-out, proxy/IP
  rotation, CAPTCHA handling, or automatic block retries without an explicit
  ethical review and a shared retailer-specific request limiter.
- Run `python -m pytest` and `python -m ruff check .` after source changes.
- Keep `CITATION.cff`, `CHANGELOG.md`, and the package version aligned for each
  release.

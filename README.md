# Grocery Delivery Availability

`grocery-delivery-availability` is a research command-line tool for collecting
postcode-level grocery delivery coverage from UK retailer websites. It
supports Amazon Fresh, Co-op, Iceland, Morrisons, Ocado, and Sainsbury's Chop
Chop.

The tool distinguishes three outcomes:

- `Yes`: the retailer returned an affirmative postcode-specific signal.
- `No`: a successful postcode-specific request explicitly indicated no usable
  service.
- `Unknown`: the result was inconclusive, including invalid or unresolved
  addresses, blocks, rate limits, timeouts, schema changes, and suspected stale
  responses.

The retailers measure different services; results are not automatically
like-for-like. See [the methodology](docs/methodology.md) before analysis.

## Responsible collection

Responsible collection is part of the executable research method, not an
optional deployment detail. The public tool defaults to sequential collection,
reuses sessions and completed results, requests only retailer-specific minimum
evidence, and preserves blocks or technical failures as `Unknown`.

Version 0.1 is intended for bounded, supervised, single-process runs. It does
not yet provide a distributed rate limiter or shared 429 circuit, so parallel
or unattended cloud collection is outside the responsible default. See
[Responsible Data Collection and Research Ethics](docs/responsible-data-collection.md)
for request costs, implemented safeguards, stop conditions, privacy boundaries,
limitations, and pre-/post-run records.

## Installation

Python 3.11 or newer is required.

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

The Docker image already contains the Playwright browser runtime:

```bash
docker build -t grocery-delivery-availability .
```

## Usage

Check one or more postcodes:

```bash
grocery-delivery-availability check \
  --retailer chopchop \
  --postcode "E1 6HQ" \
  --postcode "LS2 9JT" \
  --output output/chopchop.csv
```

Read postcodes from a CSV file:

```bash
grocery-delivery-availability check \
  --retailer coop \
  --input examples/postcodes.csv \
  --postcode-column Postcode \
  --output output/coop.csv \
  --delay 2
```

For Co-op, the validated workflow can attach to a normal Microsoft Edge
session that the operator has already opened and confirmed is usable. Launch
Edge with a dedicated debugging profile, open the Co-op storefront manually,
then run:

```bash
grocery-delivery-availability check \
  --retailer coop \
  --input examples/postcodes.csv \
  --postcode-column Postcode \
  --output output/coop.csv \
  --coop-cdp-url http://127.0.0.1:9222 \
  --evidence-dir .tmp/coop-business-responses \
  --delay 2
```

The attached Edge process must have been started with remote debugging enabled,
for example `--remote-debugging-port=9222`, and with a dedicated
`--user-data-dir`. The tool does not export or distribute that profile. It
disconnects without intentionally closing the attached browser. If Co-op
returns 403/429 or a mismatched/unknown schema, collection checkpoints the
current row and stops; resume only after manual review.

Browser-backed retailers run headlessly by default. Use `--headed` for visible
diagnostics. Existing `Yes` and `No` rows are reused with `--resume`; prior
`Unknown` rows are retried.

List available retailers:

```bash
grocery-delivery-availability retailers
```

## Output

Every CSV uses a stable common schema. Retailer-specific evidence is retained
in fields such as `brands`, `fast_delivery`, `scheduled_delivery`,
`delivery_coverage`, and `current_slot`; additional machine-readable evidence
is stored in `details_json`.

Co-op rows also record the confirmed postcode, collection coverage, query and
response timestamps, decoded delivery-slot UTC start/end, service type, and
minutes from query start to the earliest delivery start. Complete business
responses default to `.tmp/coop-business-responses`; `--evidence-dir` can place
them in another ignored runtime location.

Each observation records an ISO 8601 UTC timestamp. The software does not
claim that a result remains valid after collection.

## Reproducibility and validation

- Batch runs use bounded pacing and atomic checkpoints.
- Requested and returned postcodes are compared whenever the retailer exposes
  a returned postcode.
- Morrisons requires both an accepted address and a postcode-specific product
  catalogue with usable products.
- Amazon Fresh requires the exact `Amazon Fresh` brand among cards marked as
  delivery-available.
- Technical failures are retained as `Unknown`.
- Default automated tests are offline; live retailer smoke tests must be run
  deliberately because retailer interfaces can change.

The associated postcode audit used OS Code-Point Open version `2026.3.0`.
External postcode and research datasets are not distributed in this software
repository. See [data requirements](docs/data-requirements.md).

The most recent documented Co-op evidence is the
[15 October 2026 release validation](docs/release-validation-2026-10-15.md),
following the
[12--14 October 2026 validation](docs/coop-collection-validation-2026-10-14.md),
which followed the initially blocked
[12 October feasibility test](docs/coop-feasibility-2026-10-12.md). The broader
retailer baseline remains the
[30 September 2026 smoke test](docs/live-smoke-test-2026-09-30.md).

The Co-op adapter supports the postcode-specific workflow through either a new
Playwright context or `--coop-cdp-url`, which attaches to a normal,
already-established Edge session. Fresh isolated sessions have been blocked by
Co-op's Imperva layer, so CDP attachment is the validated local option. Access
remains environment-dependent: a block is `Unknown` and never evidence of no
delivery.

## Responsible use

Use conservative request rates, review retailer terms, and stop if a site
rejects automated access. This project does not bypass authentication,
CAPTCHAs, or anti-bot controls. The retailer interfaces are undocumented and
can change without notice. The full governance record is maintained in
[Responsible Data Collection and Research Ethics](docs/responsible-data-collection.md).

## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). Cite the exact
released version used in an analysis. For version 0.1.0, cite: Chenrui Xiao
(2026), *Grocery Delivery Availability* (v0.1.0), Zenodo,
[https://doi.org/10.5281/zenodo.23400413](https://doi.org/10.5281/zenodo.23400413).
The DOI representing all versions of the software is
[10.5281/zenodo.23400412](https://doi.org/10.5281/zenodo.23400412).

## Licence

MIT. See [`LICENSE`](LICENSE).

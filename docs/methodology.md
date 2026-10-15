# Methodology

## Unit of observation

The tool evaluates one normalized UK unit postcode at a recorded UTC time. It
does not infer results for neighbouring postcodes. Geographic aggregation to
LSOAs or Scottish Data Zones is a downstream research step.

## Retailer definitions

| Retailer | `Yes` means |
|---|---|
| Amazon Fresh | The accepted address displays the exact `Amazon Fresh` brand as delivery-available on Amazon Grocery. |
| Co-op | `storeAvailability` explicitly includes delivery; current slot availability is recorded separately. |
| Iceland | The postcode endpoint returns an explicit boolean delivery code of `true`. |
| Morrisons | The address is accepted and the selected destination's product catalogue contains usable products. |
| Ocado | The resolved address receives a `DELIVERABLE` decision. |
| Chop Chop | The postcode service identifies a serving Sainsbury's Chop Chop store. |

These definitions describe different services. Chop Chop is rapid delivery,
not Sainsbury's scheduled grocery service. Morrisons fast and scheduled modes
are reported independently. Amazon's other grocery brands are retained as
evidence but do not make Amazon Fresh itself deliverable.

## Uncertainty

`Unknown` is an analytical state, not missing data and not non-delivery. It is
used for address-resolution failures, mismatched returned postcodes, HTTP
errors, rate limits, browser challenges, timeouts, suspected cache reuse, and
unrecognised response schemas.

## Session-backed requests

Co-op, Iceland, Morrisons, and Ocado first open the retailer homepage in a
Playwright browser. Subsequent requests use that first-party browser context.
The browser is not reopened for every postcode.

Co-op can instead attach through the Chrome DevTools Protocol to a normal Edge
session that the operator has already opened and verified. Its postcode request
runs through `fetch` in the storefront page, retaining the page's first-party
session. The adapter requires the response postcode to match, records delivery
and collection separately, and decodes the Base64 slot identifier for its UTC
start, UTC end, and service type. Only a decoded `delivery` slot supplies a
delivery wait time.

Morrisons binds the resolved destination and region to the session before a
minimal product catalogue request. A unique query nonce plus `Cache-Control:
no-cache` and `Pragma: no-cache` reduce cache reuse. A response that still
reports a cache hit is classified as `Unknown`.

Amazon changes the delivery address in an HTTP session, waits for session
state to settle, and then requests a nonce-qualified grocery gateway page.

## Validation procedure

Before a research run:

1. Test known urban, remote, negative, and historically unresolved postcodes.
2. Confirm that returned postcodes match requests where a returned postcode is
   available.
3. Run a representative smoke test followed by a longer soak test.
4. Compare state distributions, HTTP statuses, schema evidence, and timings
   with the preceding validated run.
5. Stop on clustered blocks or schema failures; do not convert them to `No`.

The traffic, privacy, stop, and audit requirements governing this procedure are
part of the method and are documented in
[Responsible Data Collection and Research Ethics](responsible-data-collection.md).

## Known limitations

- Retailer endpoints are undocumented and can change without notice.
- Co-op coverage and current slots are separate in the schema, but a paired
  day/night validation is still advisable before interpreting nighttime `No`
  observations.
- Co-op access is session- and environment-dependent. On 1 and 12 October 2026,
  fresh sessions were blocked during `/api/auth/session` or
  `/api/store/set?postcode=...`; these failures are `Unknown`. A later bounded
  run in a normal, already-established Microsoft Edge session returned current
  postcode-specific business JSON. The public adapter can attach to such a
  session but does not ship or recreate its browser profile. See the
  [initial feasibility record](coop-feasibility-2026-10-12.md) and the
  [subsequent validation](coop-collection-validation-2026-10-14.md).
- Co-op delivery coverage and observed slot timing are separate measurements.
  A late first slot may reflect opening hours or exhausted capacity and does not
  by itself prove that a postcode only has scheduled service.
- A Co-op 403/429, postcode mismatch, or unknown coverage schema triggers a
  checkpointed stop. There is no automatic access-control retry.
- Morrisons historically produced an unusually high scheduled-delivery rate;
  its overall result should be treated cautiously even with catalogue
  validation. The fast-delivery field is narrower.
- Amazon brand cards can load or rotate late, so reducing the address-settle
  interval requires a new consistency test.
- Live checks establish website behaviour, not successful fulfilment of a
  real order.

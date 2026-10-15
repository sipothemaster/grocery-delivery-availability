# Co-op collection validation — 12–14 October 2026

## Outcome

The current Co-op postcode workflow remained usable in a normal,
already-established Microsoft Edge session, although fresh isolated sessions
could still be rejected by Imperva. Access is therefore environment-dependent
and must not be assumed from the endpoint alone.

## Validated workflow

1. Open the public Co-op storefront and initialise its first-party session.
2. Submit a postcode to `POST /api/store/set?postcode=...`.
3. Require `formattedPostcode` to confirm the requested postcode.
4. Read `storeAvailability` for geographic delivery coverage.
5. Treat `slotAvailability` and `firstSlot` as separate, observation-time slot
   evidence; never treat collection availability as delivery.
6. Decode the Base64 `firstSlot.id` and use its UTC start, end, and service type
   rather than constructing a time from the displayed date and hour fields.

## Bounded run evidence

The research run checked 10,529 unique postcodes that were not already resolved
by earlier evidence. It returned 10,350 `Yes`, 164 `No`, and 15 `Unknown`
coverage observations. These aggregate counts document method validation; the
postcode data and complete business responses are separate research records and
are not distributed with the software.

The run used one process, one active browser session, approximately two seconds
between postcode checks, bounded batch restarts, and a 20-minute cool-down after
HTTP 403 before a supervised recheck. No proxy, IP rotation, CAPTCHA solving,
credential automation, or access-control bypass was used. Technical failures
remained `Unknown`.

## Interpretation limit

The earliest slot is the earliest delivery opportunity visible at the recorded
query time. A later or next-day slot may reflect store opening hours, exhausted
capacity, or the local service model. It does not by itself prove that a
postcode lacks on-demand delivery. Any fast-delivery threshold must therefore
be reported as an operational classification applied to timestamped
observations, not as a permanent property of the postcode.

The public adapter now implements these semantics and can attach to an
operator-opened Edge debugging session. It does not contain the working Edge
profile, cookies, raw responses, or the completed dataset. A fresh run may
again be blocked; such a result is `Unknown`, not `No`, and the batch stops for
manual review.

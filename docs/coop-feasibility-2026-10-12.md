# Co-op collection feasibility — 12 October 2026

## Conclusion

New Co-op collection is **not currently feasible from the tested local environment**.
The normal storefront fails during session initialisation before a postcode can be
accepted, so no current postcode-specific coverage or delivery-slot decision can be
obtained. This is an access-control blocker, not evidence of non-delivery.

## What was tested

- A normal browser opened `https://shop.coop.co.uk/welcome` during UK daytime.
- The page identified itself as Co-op Shop `v3.1275.0-10816460171` and initially
  displayed the postcode form.
- During hydration, the first-party request to `/api/auth/session` was reported as
  blocked by Imperva and the page changed to `Something went wrong`.
- The current same-day entry point
  `/modals/main/enter-delivery-postcode?destination=%2Fsame-day-grocery-delivery`
  redirected to `/welcome` with the modal route retained in its `destination`
  parameter. It displayed the same postcode form.
- Submitting `LS2 9JT` through that form entered a loading state and invoked
  `/api/store/set?postcode=LS2+9JT`; Imperva blocked the request and the page changed
  to `Something went wrong`.
- A fresh local Chrome probe separately observed an initial HTTP 200 navigation,
  followed by a first-party HTTP 403 on `/welcome`. The rendered Co-op denial page
  said the request was classified as coming from outside the UK.
- A fresh isolated Microsoft Edge session was then opened directly on the same-day
  modal URL. It also received HTTP 403 and the same outside-UK denial before the
  postcode form became usable. This does not reproduce an already-established
  personal Edge session, which may have different cookies or network routing.
- `LS2 9JT` reached the postcode submission request but received no business
  response. `E1 6HQ`, `HS7 5PZ`, and `HS8 5TX` were not retried because repeating a
  rejected request would add load without testing postcode-dependent behaviour.

The live diagnostic output is under `.tmp/coop-probe/` and is intentionally ignored
by Git. It contains timestamps, first-party failure metadata, a screenshot, and any
business JSON returned; it contains no cookies, tokens, request headers, or browser
profile.

## Workflow finding

The current observed workflow is:

1. open the same-day postcode modal route, which redirects through `/welcome` and a
   `destination` parameter;
2. initialise the first-party session through `/api/auth/session`;
3. accept the postcode and call `/api/store/set?postcode=...`;
4. continue to the requested same-day destination after a successful store result.

The current UI therefore still uses the same `/api/store/set` endpoint path as the
historical workflow; the modal URL is an entry route, not a replacement API. In the
in-app browser, both session initialisation and postcode submission were blocked by
Imperva. The fresh local Chrome session was rejected even earlier by the
geographic/security layer. No postcode-specific business JSON was returned.

## Historical response semantics checked

Read-only inspection of the earlier research evidence confirmed that successful
`/api/store/set` responses included `formattedPostcode`, `storeAvailability`,
`slotAvailability`, and `firstSlot`. The Base64 `firstSlot.id` decoded to a
pipe-delimited value containing UTC start, UTC end, store ID, charge, and service
type.

For 59 historical midnight records, the displayed `date` was one day earlier than
the UK-local date implied by the decoded UTC instants. The probe therefore treats the
decoded aware instants as authoritative, verifies the service type is `delivery`,
and does not construct a datetime by concatenating `date` and `startsAt`.

## Adapter decision

The production Co-op adapter endpoint remains consistent with the current frontend,
so it was not replaced. No current postcode-matched business response was available
to validate the response schema or slot fields, so the adapter's classification and
time handling were not changed. Blocked, missing, mismatched, and unknown-schema
responses remain `Unknown`.

## Conditions for a later pilot

Resume only when an ordinary, UK-recognised research connection can load the
postcode form and complete `/api/auth/session` without a challenge or manual bypass.
Do not use proxy rotation or a geographic-control workaround. Then:

- run one process with one browser context and no automatic retries;
- start with the four control postcodes above, one request at a time;
- save the complete first-party business JSON only in an ignored run directory;
- require the returned postcode to match the requested postcode;
- separate delivery coverage from collection and current slot availability;
- use decoded UTC slot instants and convert them to `Europe/London` semantics;
- record query start/end, earliest delivery start/end, service type, and wait minutes;
- repeat the small pilot in fixed weekday trading windows before defining any
  on-demand threshold.

A later slot in one observation must not be interpreted as proof that a location only
offers scheduled delivery; store opening and capacity remain competing explanations.

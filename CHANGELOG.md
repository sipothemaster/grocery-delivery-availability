# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

## [0.1.0] - 2026-10-15

- Created an independent, package-based implementation for six UK grocery
  delivery workflows.
- Added a stable three-state output contract, resumable CSV collection,
  citation metadata, documentation, and offline tests.
- Completed a six-retailer live smoke test on 30 September 2026.
- Record browser bootstrap failures as `Unknown` rows instead of terminating
  without an output file.
- Updated Chop Chop evidence parsing for store records nested in arrays.
- Documented the 1 October 2026 manual confirmation that Co-op's storefront
  loads while Imperva blocks its session and postcode APIs; retained the Co-op
  adapter as historical methodology evidence.
- Added a retailer-specific responsible-data-collection and research-ethics
  record covering request minimisation, stop conditions, privacy, audit
  evidence, current safeguards, and the limits of version 0.1.
- Added a bounded Co-op workflow probe that records postcode confirmation,
  delivery and collection separately, and decodes delivery-slot UTC instants.
- Integrated the validated Co-op workflow into the public adapter, including
  attachment to an established Edge session, in-page first-party requests,
  structured slot timing, optional raw-response evidence, and checkpointed
  stopping on access-control or schema failures.
- Documented the 12--14 October Co-op validation in an established Microsoft
  Edge session, including conservative pacing, stop/cool-down behaviour, and
  the separation of delivery coverage from observed slot timing.
- Prepared a reproducible wheel and source-distribution release process with
  version-alignment tests and citation metadata.
- Validated the integrated Co-op adapter with four live controls, 32 repeated
  postcode-matched observations, and a live resume test on 15 October 2026.

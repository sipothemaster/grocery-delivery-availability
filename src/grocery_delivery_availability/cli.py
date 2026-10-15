"""Command-line interface for postcode-level collection."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .io import read_postcodes
from .models import Observation
from .retailers import RETAILER_LABELS, RETAILERS, create_checker
from .runner import run_batch


class _UnavailableChecker:
    def __init__(self, retailer: str, reason: str) -> None:
        self.retailer = retailer
        self.reason = reason

    def check(self, postcode: str) -> Observation:
        return Observation.unknown(postcode, self.retailer, self.reason)

    def close(self) -> None:
        return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grocery-delivery-availability",
        description="Collect postcode-level UK grocery delivery availability.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("retailers", help="List supported retailer adapters.")

    check = subparsers.add_parser("check", help="Check postcodes and write a CSV file.")
    check.add_argument("--retailer", required=True, choices=sorted(RETAILERS))
    check.add_argument("--postcode", action="append", default=[])
    check.add_argument("--input", type=Path)
    check.add_argument("--postcode-column", default="Postcode")
    check.add_argument("--output", type=Path, required=True)
    check.add_argument(
        "--delay",
        type=float,
        help="Seconds after each completed check (default: 2 for Co-op, otherwise 1.5).",
    )
    check.add_argument("--checkpoint-every", type=int, default=25)
    check.add_argument("--no-resume", action="store_true")
    check.add_argument(
        "--keep-unknown",
        action="store_true",
        help="Do not retry Unknown rows already present in the output.",
    )
    check.add_argument("--headed", action="store_true")
    check.add_argument("--browser-channel")
    check.add_argument("--browser-executable")
    check.add_argument(
        "--coop-cdp-url",
        help=(
            "Attach Co-op to an already-open Edge/Chromium debugging session, "
            "for example http://127.0.0.1:9222."
        ),
    )
    check.add_argument(
        "--evidence-dir",
        type=Path,
        help="Ignored runtime directory for complete Co-op business-response JSON.",
    )
    check.add_argument("--amazon-settle", type=float, default=5)
    check.add_argument("--morrisons-settle", type=float, default=1)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "retailers":
        for name, description in RETAILERS.items():
            print(f"{name:14} {description}")
        return 0

    postcodes = list(args.postcode)
    if args.input:
        postcodes.extend(read_postcodes(args.input, args.postcode_column))
    if not postcodes:
        raise SystemExit("Provide at least one --postcode or an --input CSV file.")
    if args.amazon_settle < 0 or args.morrisons_settle < 0:
        raise SystemExit("Settle intervals cannot be negative.")
    delay_seconds = args.delay
    if delay_seconds is None:
        delay_seconds = 2.0 if args.retailer == "coop" else 1.5
    if delay_seconds < 0:
        raise SystemExit("Delay cannot be negative.")
    evidence_dir = args.evidence_dir
    if args.retailer == "coop" and evidence_dir is None:
        evidence_dir = Path(".tmp/coop-business-responses")

    exit_code = 0
    try:
        checker = create_checker(
            args.retailer,
            headless=not args.headed,
            channel=args.browser_channel,
            executable_path=args.browser_executable,
            amazon_settle_seconds=args.amazon_settle,
            morrisons_settle_seconds=args.morrisons_settle,
            coop_cdp_url=args.coop_cdp_url,
            evidence_dir=evidence_dir,
        )
    except Exception as exc:
        reason = f"Checker initialisation failed: {type(exc).__name__}: {exc}"
        checker = _UnavailableChecker(RETAILER_LABELS[args.retailer], reason)
        exit_code = 2
    results = run_batch(
        postcodes,
        checker,
        args.output,
        delay_seconds=delay_seconds,
        checkpoint_every=args.checkpoint_every,
        resume=not args.no_resume,
        keep_unknown_on_resume=args.keep_unknown,
    )
    counts = {
        state: sum(item.deliverable.value == state for item in results)
        for state in ("Yes", "No", "Unknown")
    }
    print(
        f"Wrote {len(results)} rows to {args.output} "
        f"(Yes={counts['Yes']}, No={counts['No']}, Unknown={counts['Unknown']})."
    )
    stop_reason = getattr(checker, "stop_reason", None)
    if stop_reason:
        print(f"Collection stopped safely: {stop_reason}")
        exit_code = 2
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Resumable sequential runner with atomic checkpoints."""

from __future__ import annotations

import time
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from .io import observation_from_row, read_existing, write_observations
from .models import DeliveryState, Observation
from .postcodes import is_valid_postcode, normalize_postcode


class Checker(Protocol):
    retailer: str

    def check(self, postcode: str) -> Observation: ...

    def close(self) -> None: ...


def _ordered_unique(values: Iterable[object]) -> list[str]:
    return list(dict.fromkeys(normalize_postcode(value) for value in values if str(value).strip()))


def run_batch(
    postcodes: Iterable[object],
    checker: Checker,
    output: Path,
    *,
    delay_seconds: float = 1.5,
    checkpoint_every: int = 25,
    resume: bool = True,
    keep_unknown_on_resume: bool = False,
) -> list[Observation]:
    if delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative")
    if checkpoint_every < 1:
        raise ValueError("checkpoint_every must be positive")

    selected = _ordered_unique(postcodes)
    prior = read_existing(output) if resume else {}
    results: dict[str, Observation] = {}
    for postcode, row in prior.items():
        state = row.get("deliverable")
        if state in {DeliveryState.YES.value, DeliveryState.NO.value} or (
            keep_unknown_on_resume and state == DeliveryState.UNKNOWN.value
        ):
            results[postcode] = observation_from_row(row)

    def checkpoint() -> None:
        write_observations(
            output, (results[postcode] for postcode in selected if postcode in results)
        )

    try:
        completed_since_checkpoint = 0
        for postcode in selected:
            if postcode in results:
                continue
            if not is_valid_postcode(postcode):
                observation = Observation.unknown(
                    postcode,
                    checker.retailer,
                    "The value does not match basic UK unit-postcode syntax.",
                    address_valid=DeliveryState.NO.value,
                )
            else:
                try:
                    observation = checker.check(postcode)
                except Exception as exc:  # defensive boundary around unstable websites
                    observation = Observation.unknown(
                        postcode,
                        checker.retailer,
                        f"Unhandled retailer error: {type(exc).__name__}: {exc}",
                    )
            results[postcode] = observation
            completed_since_checkpoint += 1
            if completed_since_checkpoint >= checkpoint_every:
                checkpoint()
                completed_since_checkpoint = 0
            if getattr(checker, "stop_reason", None):
                checkpoint()
                break
            if delay_seconds:
                time.sleep(delay_seconds)
    finally:
        checker.close()
        checkpoint()

    return [results[postcode] for postcode in selected if postcode in results]

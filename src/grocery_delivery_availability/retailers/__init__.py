"""Retailer registry and public checker factory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .amazon_fresh import AmazonFreshChecker
from .chopchop import ChopChopChecker
from .coop import CoopChecker
from .ecom_platform import MorrisonsChecker, OcadoChecker
from .iceland import IcelandChecker

RETAILERS = {
    "amazon-fresh": "Amazon Fresh grocery brand availability",
    "chopchop": "Sainsbury's Chop Chop rapid delivery",
    "coop": "Co-op online grocery delivery",
    "iceland": "Iceland online grocery delivery",
    "morrisons": "Morrisons grocery delivery with fast/scheduled evidence",
    "ocado": "Ocado grocery delivery",
}

RETAILER_LABELS = {
    "amazon-fresh": "Amazon Fresh",
    "chopchop": "Chop Chop",
    "coop": "Co-op",
    "iceland": "Iceland",
    "morrisons": "Morrisons",
    "ocado": "Ocado",
}


def create_checker(
    name: str,
    *,
    headless: bool = True,
    channel: str | None = None,
    executable_path: str | None = None,
    amazon_settle_seconds: float = 5,
    morrisons_settle_seconds: float = 1,
    coop_cdp_url: str | None = None,
    evidence_dir: Path | None = None,
) -> Any:
    """Create a checker without exposing retailer-specific constructors in the CLI."""

    browser_options = {
        "headless": headless,
        "channel": channel,
        "executable_path": executable_path,
    }
    if name == "amazon-fresh":
        return AmazonFreshChecker(address_settle_seconds=amazon_settle_seconds)
    if name == "chopchop":
        return ChopChopChecker()
    if name == "coop":
        return CoopChecker(
            cdp_url=coop_cdp_url,
            evidence_dir=evidence_dir,
            **browser_options,
        )
    if name == "iceland":
        return IcelandChecker(**browser_options)
    if name == "morrisons":
        return MorrisonsChecker(
            catalog_settle_seconds=morrisons_settle_seconds,
            **browser_options,
        )
    if name == "ocado":
        return OcadoChecker(**browser_options)
    raise ValueError(f"Unknown retailer: {name}")


__all__ = ["RETAILERS", "RETAILER_LABELS", "create_checker"]

from pathlib import Path

from grocery_delivery_availability import cli
from grocery_delivery_availability.io import read_existing


def test_initialisation_failure_is_recorded_as_unknown(monkeypatch, tmp_path: Path) -> None:
    def fail(*_args, **_kwargs):
        raise RuntimeError("synthetic block")

    monkeypatch.setattr(cli, "create_checker", fail)
    output = tmp_path / "blocked.csv"
    status = cli.main(
        [
            "check",
            "--retailer",
            "coop",
            "--postcode",
            "E1 6HQ",
            "--output",
            str(output),
            "--delay",
            "0",
        ]
    )
    row = read_existing(output)["E1 6HQ"]
    assert status == 2
    assert row["deliverable"] == "Unknown"
    assert "synthetic block" in row["reason"]

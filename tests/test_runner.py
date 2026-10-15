from pathlib import Path

from grocery_delivery_availability.io import read_existing
from grocery_delivery_availability.models import DeliveryState, Observation
from grocery_delivery_availability.runner import run_batch


class FakeChecker:
    retailer = "Synthetic retailer"

    def __init__(self) -> None:
        self.checked: list[str] = []
        self.closed = False

    def check(self, postcode: str) -> Observation:
        self.checked.append(postcode)
        return Observation(
            postcode,
            self.retailer,
            DeliveryState.YES,
            "Synthetic affirmative response.",
        )

    def close(self) -> None:
        self.closed = True


class StoppingChecker(FakeChecker):
    def __init__(self) -> None:
        super().__init__()
        self.stop_reason: str | None = None

    def check(self, postcode: str) -> Observation:
        observation = super().check(postcode)
        self.stop_reason = "Synthetic access-control stop."
        return observation


def test_batch_deduplicates_checkpoints_and_marks_invalid_values_unknown(
    tmp_path: Path,
) -> None:
    output = tmp_path / "results.csv"
    checker = FakeChecker()
    results = run_batch(
        ["e1 6hq", "E1 6HQ", "invalid"],
        checker,
        output,
        delay_seconds=0,
        checkpoint_every=1,
    )
    assert checker.checked == ["E1 6HQ"]
    assert checker.closed
    assert [item.deliverable for item in results] == [
        DeliveryState.YES,
        DeliveryState.UNKNOWN,
    ]
    assert set(read_existing(output)) == {"E1 6HQ", "INVA LID"}


def test_resume_reuses_yes_but_retries_unknown(tmp_path: Path) -> None:
    output = tmp_path / "results.csv"
    first = FakeChecker()
    run_batch(["E1 6HQ", "invalid"], first, output, delay_seconds=0)

    second = FakeChecker()
    run_batch(["E1 6HQ", "invalid"], second, output, delay_seconds=0)
    assert second.checked == []
    assert second.closed


def test_batch_stops_and_checkpoints_when_checker_requests_stop(tmp_path: Path) -> None:
    output = tmp_path / "stopped.csv"
    checker = StoppingChecker()

    results = run_batch(
        ["E1 6HQ", "LS2 9JT"],
        checker,
        output,
        delay_seconds=0,
    )

    assert checker.checked == ["E1 6HQ"]
    assert checker.closed
    assert [result.postcode for result in results] == ["E1 6HQ"]
    assert set(read_existing(output)) == {"E1 6HQ"}

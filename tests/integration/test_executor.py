from pathlib import Path

import pytest

from testbreaker.domain import MutantStatus
from testbreaker.executor import run_mutant

FIXTURES = Path(__file__).parents[1] / "fixtures"
REFUND_APP = FIXTURES / "refund_app"
MUTANTS = FIXTURES / "mutants"


@pytest.mark.parametrize(
    ("patch_name", "expected_status"),
    [
        ("survived.diff", MutantStatus.SURVIVED),
        ("killed.diff", MutantStatus.KILLED),
        ("invalid.diff", MutantStatus.INVALID),
        ("syntax_invalid.diff", MutantStatus.INVALID),
    ],
)
def test_mutant_classification(patch_name: str, expected_status: MutantStatus):
    result = run_mutant(REFUND_APP, MUTANTS / patch_name)

    assert result.status is expected_status


def test_baseline_failure_stops_execution():
    result = run_mutant(FIXTURES / "failing_app", MUTANTS / "survived.diff")

    assert result.status is MutantStatus.BASELINE_FAILED
    assert result.mutated is None


def test_original_repository_remains_unchanged():
    source_path = REFUND_APP / "refund.py"
    original_source = source_path.read_text(encoding="utf-8")

    run_mutant(REFUND_APP, MUTANTS / "killed.diff")

    assert source_path.read_text(encoding="utf-8") == original_source


from pathlib import Path

from testbreaker.domain import MutantStatus
from testbreaker.executor import run_mutant


def test_missing_repository_is_invalid(tmp_path: Path):
    patch = tmp_path / "change.diff"
    patch.write_text("", encoding="utf-8")

    result = run_mutant(tmp_path / "missing", patch)

    assert result.status is MutantStatus.INVALID


def test_missing_patch_is_invalid(tmp_path: Path):
    result = run_mutant(tmp_path, tmp_path / "missing.diff")

    assert result.status is MutantStatus.INVALID

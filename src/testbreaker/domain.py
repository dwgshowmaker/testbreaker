from dataclasses import dataclass
from enum import Enum


class MutantStatus(Enum):
    SURVIVED = "survived"
    KILLED = "killed"
    INVALID = "invalid"
    BASELINE_FAILED = "baseline_failed"


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


@dataclass(frozen=True)
class MutantResult:
    status: MutantStatus
    baseline: CommandResult | None
    mutated: CommandResult | None
    message: str | None = None


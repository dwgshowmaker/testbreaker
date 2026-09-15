import ast
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tokenize
from pathlib import Path

from testbreaker.domain import CommandResult, MutantResult, MutantStatus


def _run(command: list[str], cwd: Path) -> CommandResult:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    existing_options = environment.get("PYTEST_ADDOPTS", "")
    environment["PYTEST_ADDOPTS"] = f"{existing_options} -p no:cacheprovider".strip()

    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    duration_ms = round((time.monotonic() - started) * 1000)
    return CommandResult(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_ms=duration_ms,
    )


def _syntax_error(repo_path: Path) -> str | None:
    for source_path in repo_path.rglob("*.py"):
        try:
            with tokenize.open(source_path) as source_file:
                source = source_file.read()
            ast.parse(source, filename=str(source_path))
        except (SyntaxError, UnicodeDecodeError) as error:
            return f"Python syntax validation failed for {source_path.relative_to(repo_path)}: {error}"
    return None


def _command_error(action: str, error: OSError) -> MutantResult:
    return MutantResult(
        status=MutantStatus.INVALID,
        baseline=None,
        mutated=None,
        message=f"Could not {action}: {error}",
    )


def run_mutant(repo_path: Path, patch_path: Path) -> MutantResult:
    repo_path = repo_path.resolve()
    patch_path = patch_path.resolve()

    if not repo_path.is_dir():
        return MutantResult(MutantStatus.INVALID, None, None, "Repository path does not exist.")
    if not patch_path.is_file():
        return MutantResult(MutantStatus.INVALID, None, None, "Patch file does not exist.")

    try:
        baseline = _run([sys.executable, "-m", "pytest"], repo_path)
    except OSError as error:
        return _command_error("run baseline tests", error)

    if baseline.exit_code != 0:
        return MutantResult(
            MutantStatus.BASELINE_FAILED,
            baseline,
            None,
            "The baseline test suite failed.",
        )

    try:
        with tempfile.TemporaryDirectory(prefix="testbreaker-") as temporary_directory:
            temporary_repo = Path(temporary_directory) / "repo"
            shutil.copytree(repo_path, temporary_repo)

            patch = _run(["git", "apply", str(patch_path)], temporary_repo)
            if patch.exit_code != 0:
                details = patch.stderr.strip() or patch.stdout.strip()
                message = "Patch could not be applied."
                if details:
                    message = f"{message}\n{details}"
                return MutantResult(MutantStatus.INVALID, baseline, None, message)

            syntax_error = _syntax_error(temporary_repo)
            if syntax_error is not None:
                return MutantResult(MutantStatus.INVALID, baseline, None, syntax_error)

            mutated = _run([sys.executable, "-m", "pytest"], temporary_repo)
            if mutated.exit_code == 0:
                return MutantResult(MutantStatus.SURVIVED, baseline, mutated)
            return MutantResult(MutantStatus.KILLED, baseline, mutated)
    except OSError as error:
        return MutantResult(
            MutantStatus.INVALID,
            baseline,
            None,
            f"Could not prepare mutation execution: {error}",
        )


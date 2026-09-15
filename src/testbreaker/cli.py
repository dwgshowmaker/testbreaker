from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from testbreaker.executor import run_mutant
from testbreaker.reporting import report_result

app = typer.Typer(help="Check whether pytest detects a known-bad patch.")


@app.callback()
def main() -> None:
    """Check whether pytest detects a known-bad patch."""


@app.command()
def run(
    repo: Annotated[Path, typer.Argument(help="Python repository to test")],
    patch: Annotated[Path, typer.Argument(help="Unified diff to apply")],
) -> None:
    """Run a patch against a repository's real pytest suite."""
    report_result(run_mutant(repo, patch), Console())


if __name__ == "__main__":
    app()

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from testbreaker.changes import ChangeAnalysisError, analyze_changes
from testbreaker.executor import run_mutant
from testbreaker.reporting import report_changes, report_result

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


@app.command()
def changes(
    repo: Annotated[Path, typer.Argument(help="Git repository to analyze")],
    revision_range: Annotated[str, typer.Argument(help="Git revision range, such as main...HEAD")],
) -> None:
    """Find functions and methods touched by a Git diff."""
    console = Console(stderr=True)
    try:
        targets = analyze_changes(repo, revision_range)
    except ChangeAnalysisError as error:
        console.print(f"[bold red]CHANGE_ANALYSIS_FAILED[/bold red]\n\n{error}")
        raise typer.Exit(code=1) from error
    report_changes(targets, Console())


if __name__ == "__main__":
    app()

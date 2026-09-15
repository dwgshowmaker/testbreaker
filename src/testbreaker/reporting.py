import sys

from rich.console import Console

from testbreaker.domain import MutantResult, MutantStatus


def report_result(result: MutantResult, console: Console) -> None:
    passed = "+" if sys.platform == "win32" else "✓"
    failed = "x" if sys.platform == "win32" else "✗"

    if result.status is MutantStatus.SURVIVED:
        console.print(f"Baseline\n[green]{passed}[/green] tests passed\n")
        console.print(f"Mutant\n[green]{passed}[/green] patch applied")
        console.print(f"[green]{passed}[/green] syntax valid")
        console.print(f"[green]{passed}[/green] tests passed\n")
        console.print("[bold yellow]SURVIVED[/bold yellow]\n")
        console.print("The incorrect implementation was not detected by the existing test suite.")
    elif result.status is MutantStatus.KILLED:
        console.print(f"Baseline\n[green]{passed}[/green] tests passed\n")
        console.print(f"Mutant\n[green]{passed}[/green] patch applied")
        console.print(f"[green]{passed}[/green] syntax valid")
        console.print(f"[red]{failed}[/red] tests failed\n")
        console.print("[bold green]KILLED[/bold green]\n")
        console.print("The existing test suite detected the mutation.")
    else:
        console.print(f"[bold red]{result.status.name}[/bold red]\n")
        if result.message:
            console.print(result.message)

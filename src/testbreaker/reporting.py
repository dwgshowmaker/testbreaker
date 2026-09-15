import sys

from rich.console import Console

from testbreaker.domain import ChangedTarget, MutantResult, MutantStatus


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


def report_changes(targets: list[ChangedTarget], console: Console) -> None:
    if not targets:
        console.print("No changed Python functions found.")
        return

    console.print("[bold]Changed Python targets[/bold]\n")
    current_path = None
    for target in targets:
        if target.path != current_path:
            if current_path is not None:
                console.print()
            console.print(f"[cyan]{target.path.as_posix()}[/cyan]\n")
            current_path = target.path
        changed_lines = ", ".join(str(line) for line in target.changed_lines)
        console.print(f"  [bold]{target.symbol}[/bold]")
        console.print(f"  lines {target.start_line}-{target.end_line}")
        console.print(f"  changed lines: {changed_lines}\n")

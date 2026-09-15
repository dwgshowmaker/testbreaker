import ast
import re
import subprocess
import tokenize
from collections import defaultdict
from pathlib import Path

from testbreaker.domain import ChangedFile, ChangedTarget

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


class ChangeAnalysisError(RuntimeError):
    """Raised when a repository's changes cannot be analyzed."""


def parse_changed_files(diff: str) -> list[ChangedFile]:
    changed: dict[Path, set[int]] = defaultdict(set)
    current_path: Path | None = None
    new_line: int | None = None
    new_count = 0

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            current_path = None
            new_line = None
        elif line.startswith("+++ ") and new_line is None:
            raw_path = line[4:]
            current_path = None if raw_path == "/dev/null" else Path(raw_path.removeprefix("b/"))
            if current_path is not None and current_path.suffix != ".py":
                current_path = None
        elif match := HUNK_HEADER.match(line):
            start = int(match.group(1))
            new_count = int(match.group(2) or "1")
            # For a deletion-only hunk Git points at the line before the
            # insertion position. Anchor the change to the following new line.
            new_line = start + 1 if new_count == 0 else start
        elif current_path is not None and new_line is not None:
            if line.startswith("+"):
                changed[current_path].add(new_line)
                new_line += 1
            elif line.startswith("-"):
                changed[current_path].add(new_line)
            elif line.startswith(" "):
                new_line += 1
            elif line.startswith("\\ No newline at end of file"):
                continue

    return [
        ChangedFile(path=path, changed_lines=tuple(sorted(lines)))
        for path, lines in sorted(changed.items(), key=lambda item: item[0].as_posix())
    ]


def get_changed_files(repo_path: Path, revision_range: str) -> list[ChangedFile]:
    repo_path = repo_path.resolve()
    if not repo_path.is_dir():
        raise ChangeAnalysisError(f"Repository path does not exist: {repo_path}")

    try:
        completed = subprocess.run(
            [
                "git",
                "-c",
                "core.quotePath=false",
                "diff",
                "--unified=0",
                revision_range,
                "--",
                "*.py",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ChangeAnalysisError(f"Could not run git diff: {error}") from error

    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise ChangeAnalysisError(f"Git diff failed for {revision_range}: {details}")
    return parse_changed_files(completed.stdout)


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]] = []
        self.class_names: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_names.append(node.name)
        self.generic_visit(node)
        self.class_names.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record(node)

    def _record(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        symbol = ".".join((*self.class_names, node.name))
        self.functions.append((node, symbol))
        # Nested functions are intentionally outside Phase 2.


def _targets_for_file(repo_path: Path, changed_file: ChangedFile) -> list[ChangedTarget]:
    source_path = repo_path / changed_file.path
    try:
        with tokenize.open(source_path) as source_file:
            source = source_file.read()
    except (OSError, SyntaxError, UnicodeError) as error:
        raise ChangeAnalysisError(
            f"Could not read changed Python file {changed_file.path}: {error}"
        ) from error

    try:
        tree = ast.parse(source, filename=str(changed_file.path))
    except SyntaxError as error:
        raise ChangeAnalysisError(f"Could not parse changed Python file {changed_file.path}: {error}") from error

    collector = _FunctionCollector()
    collector.visit(tree)
    source_lines = source.splitlines(keepends=True)
    targets: list[ChangedTarget] = []

    for node, symbol in collector.functions:
        decorator_lines = [decorator.lineno for decorator in node.decorator_list]
        start_line = min([node.lineno, *decorator_lines])
        end_line = node.end_lineno
        if end_line is None:
            continue
        matching_lines = tuple(
            line for line in changed_file.changed_lines if start_line <= line <= end_line
        )
        if matching_lines:
            targets.append(
                ChangedTarget(
                    path=changed_file.path,
                    symbol=symbol,
                    start_line=start_line,
                    end_line=end_line,
                    changed_lines=matching_lines,
                    source="".join(source_lines[start_line - 1 : end_line]),
                )
            )
    return targets


def analyze_changes(repo_path: Path, revision_range: str) -> list[ChangedTarget]:
    repo_path = repo_path.resolve()
    targets: list[ChangedTarget] = []
    for changed_file in get_changed_files(repo_path, revision_range):
        targets.extend(_targets_for_file(repo_path, changed_file))
    return targets

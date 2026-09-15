import subprocess
from pathlib import Path

import pytest

from testbreaker.changes import ChangeAnalysisError, analyze_changes


def _git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "testbreaker@example.com")
    _git(tmp_path, "config", "user.name", "TestBreaker")
    return tmp_path


def test_only_the_changed_function_is_returned(git_repo: Path):
    source = git_repo / "service.py"
    source.write_text("def foo():\n    return 1\n\ndef bar():\n    return 2\n", encoding="utf-8")
    base = _commit(git_repo, "base")
    source.write_text("def foo():\n    return 10\n\ndef bar():\n    return 2\n", encoding="utf-8")
    _commit(git_repo, "change foo")

    targets = analyze_changes(git_repo, f"{base}...HEAD")

    assert [target.symbol for target in targets] == ["foo"]
    assert targets[0].path == Path("service.py")
    assert targets[0].changed_lines == (2,)
    assert targets[0].source == "def foo():\n    return 10\n"


def test_multiple_functions_and_files_are_returned(git_repo: Path):
    first = git_repo / "first.py"
    second = git_repo / "second.py"
    first.write_text("def foo():\n    return 1\n\ndef bar():\n    return 2\n", encoding="utf-8")
    second.write_text("def baz():\n    return 3\n", encoding="utf-8")
    base = _commit(git_repo, "base")
    first.write_text("def foo():\n    return 10\n\ndef bar():\n    return 20\n", encoding="utf-8")
    second.write_text("def baz():\n    return 30\n", encoding="utf-8")
    _commit(git_repo, "change all")

    targets = analyze_changes(git_repo, f"{base}...HEAD")

    assert [(target.path, target.symbol) for target in targets] == [
        (Path("first.py"), "foo"),
        (Path("first.py"), "bar"),
        (Path("second.py"), "baz"),
    ]


def test_method_async_and_decorated_function_are_supported(git_repo: Path):
    source = git_repo / "users.py"
    source.write_text(
        "class UserService:\n"
        "    def update(self):\n"
        "        return 1\n\n"
        "def route(path):\n"
        "    return lambda function: function\n\n"
        "@route('/users')\n"
        "async def get_users():\n"
        "    return []\n",
        encoding="utf-8",
    )
    base = _commit(git_repo, "base")
    source.write_text(
        "class UserService:\n"
        "    def update(self):\n"
        "        return 2\n\n"
        "def route(path):\n"
        "    return lambda function: function\n\n"
        "@route('/people')\n"
        "async def get_users():\n"
        "    return [1]\n",
        encoding="utf-8",
    )
    _commit(git_repo, "change callables")

    targets = analyze_changes(git_repo, f"{base}...HEAD")

    assert [target.symbol for target in targets] == ["UserService.update", "get_users"]
    decorated = targets[1]
    assert decorated.start_line == 8
    assert decorated.source.startswith("@route('/people')\nasync def get_users()")


def test_new_function_is_returned_and_module_change_is_ignored(git_repo: Path):
    source = git_repo / "calculate.py"
    source.write_text("RATE = 1\n", encoding="utf-8")
    base = _commit(git_repo, "base")
    source.write_text(
        "RATE = 2\n\ndef calculate_tax(amount):\n    return amount * RATE\n",
        encoding="utf-8",
    )
    _commit(git_repo, "add function")

    targets = analyze_changes(git_repo, f"{base}...HEAD")

    assert [target.symbol for target in targets] == ["calculate_tax"]
    assert targets[0].changed_lines == (3, 4)


def test_deleted_line_inside_function_still_returns_function(git_repo: Path):
    source = git_repo / "debug.py"
    source.write_text(
        "def debug():\n    pass\n\ndef foo():\n    debug()\n    return 1\n",
        encoding="utf-8",
    )
    base = _commit(git_repo, "base")
    source.write_text(
        "def debug():\n    pass\n\ndef foo():\n    return 1\n",
        encoding="utf-8",
    )
    _commit(git_repo, "remove debug call")

    targets = analyze_changes(git_repo, f"{base}...HEAD")

    assert [target.symbol for target in targets] == ["foo"]
    assert targets[0].changed_lines == (5,)


def test_multiple_hunks_in_one_function_are_aggregated(git_repo: Path):
    source = git_repo / "long_function.py"
    original_lines = ["def foo():", *[f"    value_{number} = {number}" for number in range(1, 15)], "    return value_1"]
    source.write_text("\n".join(original_lines) + "\n", encoding="utf-8")
    base = _commit(git_repo, "base")
    changed_lines = original_lines.copy()
    changed_lines[2] = "    value_2 = 20"
    changed_lines[13] = "    value_13 = 130"
    source.write_text("\n".join(changed_lines) + "\n", encoding="utf-8")
    _commit(git_repo, "two distant changes")

    targets = analyze_changes(git_repo, f"{base}...HEAD")

    assert len(targets) == 1
    assert targets[0].changed_lines == (3, 14)


def test_non_python_change_returns_empty_list(git_repo: Path):
    readme = git_repo / "README.md"
    readme.write_text("old\n", encoding="utf-8")
    base = _commit(git_repo, "base")
    readme.write_text("new\n", encoding="utf-8")
    _commit(git_repo, "docs")

    assert analyze_changes(git_repo, f"{base}...HEAD") == []


def test_invalid_revision_fails_clearly(git_repo: Path):
    (git_repo / "app.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    _commit(git_repo, "base")

    with pytest.raises(ChangeAnalysisError, match="Git diff failed"):
        analyze_changes(git_repo, "does-not-exist...HEAD")


def test_syntax_error_fails_clearly(git_repo: Path):
    source = git_repo / "app.py"
    source.write_text("def foo():\n    return 1\n", encoding="utf-8")
    base = _commit(git_repo, "base")
    source.write_text("def foo(:\n    return 2\n", encoding="utf-8")
    _commit(git_repo, "invalid Python")

    with pytest.raises(ChangeAnalysisError, match="Could not parse changed Python file app.py"):
        analyze_changes(git_repo, f"{base}...HEAD")


def test_analysis_does_not_modify_repository(git_repo: Path):
    source = git_repo / "app.py"
    source.write_text("def foo():\n    return 1\n", encoding="utf-8")
    base = _commit(git_repo, "base")
    source.write_text("def foo():\n    return 2\n", encoding="utf-8")
    _commit(git_repo, "change")
    before = {path.relative_to(git_repo): path.read_bytes() for path in git_repo.rglob("*") if path.is_file()}

    analyze_changes(git_repo, f"{base}...HEAD")

    after = {path.relative_to(git_repo): path.read_bytes() for path in git_repo.rglob("*") if path.is_file()}
    assert after == before

# TestBreaker

TestBreaker checks whether an existing Python test suite detects a known-bad implementation.
It can run a supplied mutation against real tests and discover Python functions changed by a
Git revision range.

## Install

Python 3.12 or newer, `uv`, and Git are required.

```bash
uv sync
```

## Run

```bash
uv run testbreaker run tests/fixtures/refund_app tests/fixtures/mutants/survived.diff
```

- `SURVIVED` means the patch applied, remained valid Python, and all tests still passed.
- `KILLED` means the patch applied but at least one test failed.
- `INVALID` means execution could not be prepared, the patch failed to apply, or it introduced
  invalid Python syntax.
- `BASELINE_FAILED` means the repository's tests already failed before mutation.

## Analyze changed functions

```bash
uv run testbreaker changes . main...HEAD
```

This reads the real Git diff and reports functions, methods, and async functions containing
changed new-version lines. Reported source includes decorators.

## Current limitations

Mutation execution supports only local Python projects tested with pytest and patches accepted
by `git apply`. It does not generate mutations or provide a sandbox. TestBreaker executes the
target repository's test suite. Only run it on code you trust.

Phase 2 currently discovers function and method changes only. Module-level and class-level
changes are ignored, as are nested functions. Functions deleted entirely by a diff are not
emitted as `ChangedTarget` because they no longer exist in the current source. Change analysis
supports only `.py` files and does not track renamed symbols.

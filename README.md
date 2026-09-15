# TestBreaker

TestBreaker checks whether an existing Python test suite detects a known-bad implementation.
Its Phase 1 command takes a repository and a unified diff, applies the diff only in a temporary
copy, and runs the repository's real pytest suite.

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

## Current limitations

Phase 1 supports only local Python projects tested with pytest and patches accepted by
`git apply`. It does not generate mutations or provide a sandbox. TestBreaker executes the
target repository's test suite. Only run it on code you trust.


# Contributing

## Tests

When contributing pull requests, it's a good idea to run basic checks locally:

```bash
# install development dependencies
tpi (master)$ pip install pre-commit -r requirements-dev.txt
tpi (master)$ pre-commit install  # install pre-commit checks
tpi (master)$ pytest              # run all tests
```

## Layout

Most of the magic lives in [`tpi/__init__.py`](./tpi/__init__.py).

- [tpi/](./tpi/)
  - [`__init__.py`](./tpi/__init__.py)
  - [`main.py`](./tpi/main.py)
    - `get_main_parser()` - returns `tpi`'s own parser object
    - `main()` - `tpi`'s own CLI application

## Releases

Tests and deployment are handled automatically by continuous integration. Simply
tag a commit `v{major}.{minor}.{patch}` and wait for a draft release to appear
at <https://github.com/iterative/tpi/releases>. Tidy up the draft's
description before publishing it.

Note that tagging a release is possible by commenting `/tag vM.m.p HASH` in an
issue or PR.

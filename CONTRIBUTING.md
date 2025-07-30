# Contributing

Thanks for wanting to contribute!

## Running the Test Suite

Install the test dependencies and run pytest from the project root:

```bash
pip install -e .[test]
ruff check src tests
pytest
```

Tests live under the `tests/` directory and cover basic functionality such as template loading and the CLI.

## Linting and Build Steps

We use [ruff](https://github.com/astral-sh/ruff) for linting. The command above will check the `src` and `tests` folders. The project is a standard Python package built with `setuptools`; nothing special is required when packaging beyond running the tests and linter.

## Submitting Pull Requests

1. Fork the repository and create a feature branch.
2. Ensure `ruff check` and `pytest` succeed.
3. Open a pull request describing the changes and reference any related issues.

Happy hacking!

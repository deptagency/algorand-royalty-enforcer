# ARC-18 Implementation

Based on the example at https://github.com/algorand-devrel/royalty/

This implementation adds various tests and some additional checks.

TODO:

- [ ] Finalize enforcer contract implementation
- [ ] Build script
- [ ] Setup automated deploy/release workflows
- [ ] Implement marketplace contract
- [ ] Additional test cases
- [ ] Perform third-party audits
- [ ] Address any issues that come up from audits

## Requirements

- [Python 3.10+][python]
- [Poetry][poetry]
- [Algorand Sandbox][sandbox]

## Setup

```bash
poetry shell # optionally create or start virtual environment with poetry
poetry install # install dependencies
```

> In VS Code, make sure you specify the right Python interpreter. You can find the path to the one Poetry setup via:
>
> ```bash
> which python | pbcopy
> ```
>
> And then run the VS Code command `Python: Select Interpreter` and paste in the path.

## Build contracts

```bash
./build.sh
```

## Run tests

> When running tests, be sure to run the Algorand Sandbox in the default "SandNet" mode. The tests assume Algod and KMD are available with the default URLs, ports, and tokens.

```bash
poetry run pytest -n auto
```

[python]: https://www.python.org/
[poetry]: https://python-poetry.org/docs/
[sandbox]: https://github.com/algorand/sandbox

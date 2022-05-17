# Algorand Royalty Enforcer Implementation

This is an implementation of ARC-18 and (partial) ARC-20. It is based on the example at https://github.com/algorand-devrel/royalty/. This implementation adds various tests and some additional checks.

- [ARC-18 PR](https://github.com/algorandfoundation/ARCs/pull/70) / [ARC-18](https://github.com/barnjamin/ARCs/blob/royalty/ARCs/arc-0018.md)
- [ARC-20 PR](https://github.com/algorandfoundation/ARCs/pull/91) / [ARC-20](https://github.com/aldur/ARCs/blob/smartasa/ARCs/arc-00xx.md)

TODO:

- [x] Implement enforcer contract and tests
- [x] Build script
- [x] Setup automated deploy/release workflows
- [x] Placeholder enforcer contract to match the ABI of ARC-18 and ARC-20
- [ ] Implement relevant ARC-20 ABI
- [ ] Implement marketplace contract for ALGO and generic ASA and tests
- [ ] Perform third-party audits
- [ ] Address any issues that come up from audits
- [ ] Additional test cases
- [ ] Finalize contract implementations and make them immutable

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

> TODO

```bash
./build.sh
```

## Run tests

> When running tests, be sure to run the Algorand Sandbox in the default "SandNet" mode. The tests assume Algod and KMD are available with the default URLs, ports, and tokens.

```bash
# outside of poetry shell
poetry run pytest

# inside poetry shell
pytest
```

Add `-n 4` to run tests in parallel using the desired number of threads (or `-n auto` to use max).

[python]: https://www.python.org/
[poetry]: https://python-poetry.org/docs/
[sandbox]: https://github.com/algorand/sandbox

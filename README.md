# ARC-18 Implementation

Based on the example at https://github.com/algorand-devrel/royalty/

Also see the ARC-18 pull request at https://github.com/algorandfoundation/ARCs/pull/70

And the ARC-18 spec at https://github.com/barnjamin/ARCs/blob/royalty/ARCs/arc-0018.md

This implementation adds various tests and some additional checks.

TODO:

- [x] Implement enforcer contract and tests
- [ ] Implement marketplace contract and tests
- [ ] Build script
- [ ] Setup automated deploy/release workflows
- [ ] Perform third-party audits
- [ ] Address any issues that come up from audits
- [ ] Additional test cases
- [ ] Finalize contract implementations

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
# outside of poetry shell
poetry run pytest -n auto

# inside poetry shell
pytest -n auto
```

[python]: https://www.python.org/
[poetry]: https://python-poetry.org/docs/
[sandbox]: https://github.com/algorand/sandbox

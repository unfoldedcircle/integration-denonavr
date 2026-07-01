# Code Guidelines

- Code line length: 120
- Use double quotes as default (don't mix and match for simple quoting).
- Configuration:
    - `pyproject.toml` for Ruff and Pyright.  

## Tooling

Install all code linting tools:

```shell
pip3 install -r test-requirements.txt
```

### Verify

The following tests are run as GitHub action for each push on the main branch and for pull requests.
They can also be run anytime on a local developer machine:

```shell
python -m ruff check intg-denonavr tests
python -m ruff format --check intg-denonavr tests
python -m pyright
```

There's also helper wrapper scripts for the above commands: [lint.sh](../lint.sh).

Linting integration in PyCharm/IntelliJ IDEA: enable Pyright and Ruff in Settings, Python, Tools

### Format Code

```shell
python -m ruff format intg-denonavr tests
```

## Language Texts

Only end-user texts must be prepared for translation with the Python [gettext](https://docs.python.org/3.11/library/gettext.html)
module. Helper functions are defined in [i18n.py](../intg-denonavr/i18n.py).

- Do not translate log messages.
- See the setup-flow code on how to use language texts.
- For more information, see [i18n.md](i18n.md).

For a pull request, a properly updated English reference language file [intg-denonavr/locales/en_US/LC_MESSAGES/intg-denonavr.po](../intg-denonavr/locales/en_US/LC_MESSAGES/intg-denonavr.po)
is appreciated, but not mandatory. We understand that it can be a challenge if gettext hasn't been used before and the
development machine is Windows :-) 

Minimally required are wrapped language texts in the Python code. A pull request reviewer can easily update the language
files after merging the PR if the translations are properly prepared in the Python code.

## Third-Party Libraries

The use of third-party libraries is encouraged when specific functionality is not provided by Python's standard library.
However, since this integration is included in the Remote firmware, the following requirements must be met:

### License Requirements

- Verify that the library's license is compatible with the project's [Mozilla Public License 2.0](https://choosealicense.com/licenses/mpl-2.0/).
- Prohibited licenses:
    - GPLv3 and its variants.
- The library's license information must be retrievable with the `pip-licenses` tool.

### Maintenance and Security

- Libraries must be actively maintained with:
    - Regular updates and bug fixes.
    - Updated dependencies.
    - Remain compatible with the Python version used in the integration.
- Specify version requirements:
    - Use semantic versioning in requirements.txt
    - Pin library version for stability.

### Approval Process

- The Unfolded Circle core team must approve any external library.  
  Please reach out before opening a pull request with a GitHub issue or a direct message. 
- Approval documentation required in:
    - GitHub issue or pull request.
    - Include justification for the library.
    - List alternatives considered.
- Non-approved libraries will result in declined pull requests.


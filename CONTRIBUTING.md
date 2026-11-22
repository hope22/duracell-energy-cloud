# Contributing

Use Python 3.12 and install `requirements-dev.txt` in a virtual environment. Run `python -m pytest`, `ruff check .` and `python -m compileall -q custom_components` before proposing a change. GitHub additionally runs HACS and Hassfest validation.

Use synthetic API fixtures only. Keep network access mocked in tests. Preserve existing unique IDs and config-entry compatibility. Verify any new API field or sign convention against real observations before adding it. Battery control endpoints are outside the current scope.

Describe the problem, resulting behavior, tests and device compatibility in pull requests. Do not attach live account captures.

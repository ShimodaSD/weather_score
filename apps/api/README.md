# Wind Score API

From this directory, install the project and start the API:

```bash
uv sync
uv run uvicorn main:app --reload
```

Dependencies and packaging are configured in the repository-root `pyproject.toml`.
uv discovers that project from this directory and installs `src/weather_score`
as an editable package. For IDE launches, select the repository-root
`.venv/bin/python` interpreter.

Run checks from this directory with `uv run pytest ../../tests` and
`uv run ruff check ../../src . ../../tests`.

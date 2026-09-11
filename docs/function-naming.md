# Function naming

Python functions use `snake_case` and follow `verb_object[_qualifier]`.

Use the verb that describes the function's behavior:

- `fetch_` performs remote or database I/O.
- `calculate_` performs a deterministic calculation.
- `get_` returns already-available local state.
- `create_` constructs a new object.
- Domain verbs such as `geocode_`, `score_`, `grade_`, and `authenticate_` are
  preferred when they describe the operation more precisely.
- A leading `_` marks a function that is private to its module.

Put the object immediately after the verb and add context last. For example,
use `fetch_current_weather`, `calculate_temperature_penalty`, and
`score_activity_at_address`. Do not include a provider name when the module
already supplies that context.

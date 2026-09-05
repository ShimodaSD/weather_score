# Implementation notes

## Python documentation convention

Python files use executable code and runtime docstrings without inline or block
`#` comments. Implementation rationale, equations, research citations,
limitations, and change summaries belong in Markdown under `docs/`.

## Pace-aware run grade

The change adds a bearer-protected `POST /grade/run` endpoint, normalized
request and response models, an independent scoring module, and automated
tests.

Average pace is converted from minutes per kilometre to running speed. The
signed route-relative wind component is combined with running speed to
calculate relative air speed. Negative wind values represent tailwinds, and
relative air speed cannot fall below zero. Tailwind benefit is reported
independently but does not increase the suitability score above 100.

Input validation rejects non-positive or non-finite pace, non-finite wind, and
WBGT values outside -50 to 60 degrees Celsius. Tests cover ideal, poor,
boundary, missing, invalid, tailwind, pace-dependent, and extreme conditions.

Scientific equations, citations, and limitations are documented in
[run-grade.md](run-grade.md).

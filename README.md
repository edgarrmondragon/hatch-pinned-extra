<div align="center">

<h1>hatch-pinned-extra</h1>

[![License][license-badge]][license]
[![GitHub last commit][commits-latest-badge]][commits-latest]
[![PyPI - Downloads][pypi-downloads-badge]][pypi-downloads]
[![uv][uv-badge]][uv]

Hatch plugin that adds a packaging [_extra_][extras] to the wheel metadata with pinned dependencies from [`uv.lock`][uvlock].

</div>

## Usage

```toml
# pyproject.toml
[build-system]
requires = [
    "hatchling",
    "hatch-pinned-extra",
]
build-backend = "hatchling.build"

[tool.hatch.metadata.hooks.pinned_extra]
name = "pinned"
```

If your package doesn't have any optional dependencies already, you will need to mark them as _dynamic_:

```toml
# pyproject.toml
[project]
dynamic = [
    "optional-dependencies",
]
```

[license]: https://pypi.python.org/pypi/hatch-pinned-extra
[license-badge]: https://img.shields.io/pypi/l/hatch-pinned-extra.svg

[commits-latest-badge]: https://img.shields.io/github/last-commit/edgarrmondragon/hatch-pinned-extra
[commits-latest]: https://github.com/edgarrmondragon/hatch-pinned-extra/commit/main

[pypi-downloads-badge]: https://img.shields.io/pypi/dm/hatch-pinned-extra
[pypi-downloads]: https://pypi.python.org/pypi/hatch-pinned-extra

[uv-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json
[uv]: https://github.com/astral-sh/uv

[extras]: https://packaging.python.org/en/latest/specifications/core-metadata/#provides-extra-multiple-use
[uvlock]: https://github.com/astral-sh/uv

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
    "hatch-pinned-extra>=0.0.1,<0.1.0",
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

### Reading pinned dependencies from `pylock.toml` file

To use a [`pylock.toml` file][pylock-spec] instead of `uv.lock`, set `lockfile` to the file path:

```toml
[tool.hatch.metadata.hooks.pinned_extra]
lockfile = "pylock.prod.toml"
```

> [!NOTE]
> `pylock.toml` files may produce less precise environment markers than `uv.lock` because the
> pylock format does not carry the resolver's internal per-Python-version splits. For example,
> a `uv.lock`-derived pinned requirement might read
> `anyio==4.13.0; python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")`
> while the equivalent from a `pylock.toml` would be `anyio==4.13.0; python_full_version >= "3.10"`.

### Enabling the Plugin

The plugin requires the `HATCH_PINNED_EXTRA_ENABLE` environment variable to be set to a truthy value to activate (e.g. `1`, `true`, `yes`, `on`). This design allows you to control when pinned dependencies are included:

```bash
# Build with pinned dependencies
HATCH_PINNED_EXTRA_ENABLE=1 uv build

# Update lockfile without constraints from pinned dependencies
uv lock --upgrade
```

This approach solves the circular dependency issue where pinned dependencies become constraints during `uv lock --upgrade`, preventing actual upgrades.

[commits-latest]: https://github.com/edgarrmondragon/hatch-pinned-extra/commit/main
[commits-latest-badge]: https://img.shields.io/github/last-commit/edgarrmondragon/hatch-pinned-extra
[extras]: https://packaging.python.org/en/latest/specifications/core-metadata/#provides-extra-multiple-use
[license]: https://pypi.python.org/pypi/hatch-pinned-extra
[license-badge]: https://img.shields.io/pypi/l/hatch-pinned-extra.svg
[pylock-spec]: https://packaging.python.org/en/latest/specifications/pylock-toml/
[pypi-downloads]: https://pypi.python.org/pypi/hatch-pinned-extra
[pypi-downloads-badge]: https://img.shields.io/pypi/dm/hatch-pinned-extra
[uv]: https://github.com/astral-sh/uv
[uv-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json
[uvlock]: https://github.com/astral-sh/uv

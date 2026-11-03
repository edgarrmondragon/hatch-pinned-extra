<div align="center">

<h1>hatch-pinned-extra</h1>

[![License][license-badge]][license]
[![GitHub last commit][commits-latest-badge]][commits-latest]
[![PyPI - Downloads][pypi-downloads-badge]][pypi-downloads]
[![Hatch project][hatch-badge]][hatch]

Hatch plugin that adds a `pinned` packaging [_extra_][extras] to the [core metadata][core-metadata] with pinned dependencies from [`uv.lock`][uvlock] or [`pylock.toml`][pylock-spec].

</div>

## Contents

- [Requirements](#requirements)
- [Usage](#usage)
  - [Combining static and dynamic optional dependencies](#combining-static-and-dynamic-optional-dependencies)
  - [Configuration](#configuration)
  - [Enabling the plugin at build time](#enabling-the-plugin-at-build-time)
  - [Reading pinned dependencies from pylock.toml file](#reading-pinned-dependencies-from-pylocktoml-file)
- [Limitations](#limitations)

## Requirements

- Python 3.10+
- Hatchling 1.27+
- For `uv.lock`: a _version 1_ lockfile. It is the version used in tests, so a future lockfile version may not work with this plugin.
- For `pylock.toml`: a compliant lockfile.

## Usage

```toml
# pyproject.toml
[build-system]
requires = [
    "hatchling",
    "hatch-pinned-extra>=0.4.0,<1",
]
build-backend = "hatchling.build"

# Leaving this empty is fine, as it registers the plugin
# and will result in using the default settings
[tool.hatch.metadata.hooks.pinned_extra]
```

The plugin needs [`optional-dependencies`][optional-dependencies] to be declared as [_dynamic_][dynamic-fields]:

```toml
# pyproject.toml
[project]
dynamic = [
    "optional-dependencies",
]
```

### Combining static and dynamic optional dependencies

> [!IMPORTANT]
> At the moment, `hatchling` does not support including static values in `optional-dependencies` when the field is also included in `dynamic`.
> Once [PEP 808][pep-808] is supported by Hatchling (see [hatch#2443](https://github.com/pypa/hatch/issues/2443) and [hatch#2463](https://github.com/pypa/hatch/pull/2463)), you'll be able to use this plugin alongside static `optional-dependencies`:
>
> ```toml
> # pyproject.toml
> [project]
> dynamic = [ "optional-dependencies" ]
>
> [project.optional-dependencies]
> cli = [ "click" ]
> ```

### Configuration

- `extra-name`: the name users will include when installing the package, e.g. `pip install my-package[<extra-name>]`. Defaults to `pinned`.

- `lockfile`: name of the lockfile, expected to be at root of the project tree. Defaults to `uv.lock`. `pylock.*.toml` files are also supported.

### Enabling the plugin at build time

The plugin requires the `HATCH_PINNED_EXTRA_ENABLE` environment variable to be set to a truthy value (e.g. `1`, `true`, `yes`, `on`) to activate. This design allows you to control when pinned dependencies are included:

```bash
# Build with pinned dependencies
HATCH_PINNED_EXTRA_ENABLE=1 uv build

# Update lockfile without constraints from pinned dependencies
uv lock --upgrade
```

This approach solves the circular dependency issue where pinned dependencies become constraints during `uv lock --upgrade`, preventing actual upgrades.

If `HATCH_PINNED_EXTRA_ENABLE` is not set, the plugin will emit a `UserWarning` and skip the extra. Some build frontends may surface this warning to you:

```console
$ uvx --with build python -m build . --wheel
* Creating isolated environment: venv+pip...
* Installing packages in isolated environment:
  - hatch_pinned_extra
  - hatchling
* Getting build dependencies for wheel...
* Installed build dependency versions:
  - hatch-pinned-extra==0.4.1
  - hatchling==1.33.0
* Building wheel...
WARNING HATCH_PINNED_EXTRA_ENABLE is not set, pinned extra is disabled
Successfully built project-0.1.0-py3-none-any.whl
```

### Reading pinned dependencies from `pylock.toml` file

> [!NOTE]
> Added in v0.4.0.

To use a [`pylock.toml` file][pylock-spec] instead of `uv.lock`, configure `lockfile`:

```toml
[tool.hatch.metadata.hooks.pinned_extra]
lockfile = "pylock.prod.toml"
```

## Limitations

- Combining this plugin with static `optional-dependencies`. See [the note above](#combining-static-and-dynamic-optional-dependencies) above regarding PEP 808 support in Hatchling.

- `uv.lock` workspace members have their dependencies dropped. This might be addressed in a future release.

- For `pylock.toml`, the `pinned` extra will contain all the dependencies in `pylock.toml`, so you'll want to make sure it includes only runtime or relevant dependencies, e.g. by generating it with `uv export --format pylock.toml --no-dev`.

- `pylock.toml` files may produce less precise environment markers than `uv.lock` because some producers may not add the resolver's internal per-Python-version splits.

  For example, a `uv.lock`-derived pinned requirement might read `anyio==4.13.0; python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")`, while the equivalent from a `pylock.toml` could be `anyio==4.13.0; python_full_version >= "3.10"`.

[commits-latest]: https://github.com/edgarrmondragon/hatch-pinned-extra/commit/main
[commits-latest-badge]: https://img.shields.io/github/last-commit/edgarrmondragon/hatch-pinned-extra
[core-metadata]: https://packaging.python.org/en/latest/specifications/core-metadata
[dynamic-fields]: https://packaging.python.org/en/latest/specifications/pyproject-toml/#dynamic
[extras]: https://packaging.python.org/en/latest/specifications/core-metadata/#provides-extra-multiple-use
[hatch]: https://github.com/pypa/hatch
[hatch-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pypa/hatch/master/docs/assets/badge/v0.json
[license]: https://github.com/edgarrmondragon/hatch-pinned-extra/blob/main/LICENSE
[license-badge]: https://img.shields.io/pypi/l/hatch-pinned-extra.svg
[optional-dependencies]: https://packaging.python.org/en/latest/specifications/pyproject-toml/#optional-dependencies
[pep-808]: https://peps.python.org/pep-0808
[pylock-spec]: https://packaging.python.org/en/latest/specifications/pylock-toml/
[pypi-downloads]: https://pypistats.org/packages/hatch-pinned-extra
[pypi-downloads-badge]: https://img.shields.io/pypi/dm/hatch-pinned-extra
[uvlock]: https://github.com/astral-sh/uv

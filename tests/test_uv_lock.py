#
#  Copyright © 2025 Edgar Ramírez-Mondragón <edgarrm358@gmail.com>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#  OR OTHER DEALINGS IN THE SOFTWARE.
#

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

from hatch_pinned_extra import PinnedExtraMetadataHook
from hatch_pinned_extra._compat import read_toml
from hatch_pinned_extra._uv import parse_pinned_deps_from_uv_lock


@pytest.fixture
def lock() -> dict[str, Any]:
    return read_toml(Path("fixtures/lockfiles/project/uv.lock"))


@pytest.fixture
def lock_with_extras() -> dict[str, Any]:
    return read_toml(Path("fixtures/lockfiles/extras/uv.lock"))


def test_parse_pinned_deps_from_uv_lock(lock: dict[str, Any]) -> None:
    reqs = parse_pinned_deps_from_uv_lock(
        lock,
        dependencies=["annotated-types", "anyio"],
    )
    assert reqs[0].name == "annotated-types"
    assert reqs[0].version == Version("0.7.0")
    assert str(reqs[0].marker) == 'python_full_version == "3.9.*" or python_full_version < "3.9"'

    assert reqs[1].name == "annotated-types"
    assert reqs[1].version == Version("0.8.0")
    assert (
        str(reqs[1].marker)
        == '(python_full_version >= "3.13" or (python_full_version >= "3.11" and python_full_version < "3.13")) or python_full_version == "3.10.*"'  # ruff: ignore[line-too-long]
    )

    assert reqs[2].name == "anyio"
    assert reqs[2].version == Version("4.5.2")
    assert str(reqs[2].marker) == 'python_full_version < "3.9"'

    assert reqs[3].name == "anyio"
    assert reqs[3].version == Version("4.12.1")
    assert str(reqs[3].marker) == 'python_full_version == "3.9.*"'

    assert reqs[4].name == "anyio"
    assert reqs[4].version == Version("4.15.1")
    assert str(reqs[4].marker) == (
        '(python_full_version >= "3.13" '
        'or (python_full_version >= "3.11" and python_full_version < "3.13")) '
        'or python_full_version == "3.10.*"'
    )

    assert reqs[5].name == "exceptiongroup"


def test_recursive_extras_resolution(lock_with_extras: dict[str, Any]) -> None:
    """Test that all dependencies from fastapi[standard] and its recursive extras are included."""
    # This matches the dependency in fixtures/extras/pyproject.toml
    reqs = parse_pinned_deps_from_uv_lock(
        lock_with_extras,
        dependencies=["fastapi[standard]>=0.115.12"],
    )
    names = {req.name for req in reqs}

    # Direct and transitive dependencies from fastapi[standard] and its recursive extras
    expected = {
        "fastapi",
        "pydantic",
        "starlette",
        "typing-extensions",
        "email-validator",
        "dnspython",
        "idna",
        "fastapi-cli",
        "rich-toolkit",
        "typer",
        "rich",
        "click",
        "colorama",
        "uvicorn",
        "httpx",
        "jinja2",
        "python-multipart",
        "pyyaml",
        "h11",
        "httpcore",
        "certifi",
        "anyio",
        "exceptiongroup",
        "markdown-it-py",
        "mdurl",
        "pygments",
        "shellingham",
        "markupsafe",
        "uvloop",
    }
    # Check that all expected dependencies are present
    missing = expected - names
    assert not missing, f"Missing dependencies in pinned output: {missing}"


def test_optional_dep_markers_preserved(lock_with_extras: dict[str, Any]) -> None:
    """Test that environment markers on optional dependencies are preserved (issue #55).

    When a dep listed under [package.optional-dependencies] in uv.lock has a marker
    (e.g., sys_platform != 'win32'), that marker must be propagated to the generated
    Requires-Dist entry so platform-specific packages are not installed unconditionally.
    """
    reqs = parse_pinned_deps_from_uv_lock(
        lock_with_extras,
        dependencies=["fastapi[standard]>=0.115.12"],
    )

    req = next((req for req in reqs if req.name == "uvloop"), None)
    assert req, "uvloop should be included as a transitive dependency"
    assert str(req.marker) == (
        '(platform_python_implementation != "PyPy" and sys_platform != "cygwin") '
        'and sys_platform != "win32"'
    )


def test_update_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    metadata: dict[str, Any] = {
        "dependencies": [
            "anyio>=4.5.2",
            "boto3>=1.36.15",
            "colorama; sys_platform == 'win32'",
            "exceptiongroup>=1.2.2",
            "importlib-resources; python_version < '3.10'",
            "fastapi>=0.115.8",
        ],
        "optional-dependencies": {
            "dev": [
                "pytest>=8; python_version >= '3.13'",
                "pytest>=7,<8; python_version < '3.13'",
            ],
        },
    }
    hook = PinnedExtraMetadataHook("fixtures/lockfiles/project", {"extra-name": "pinned"})

    dst_metadata = deepcopy(metadata)
    hook.update(dst_metadata)

    assert dst_metadata["dependencies"] == metadata["dependencies"]
    assert dst_metadata["optional-dependencies"]["dev"] == metadata["optional-dependencies"]["dev"]

    botos = [
        Requirement(dep)
        for dep in dst_metadata["optional-dependencies"]["pinned"]
        if dep.startswith("boto3")
    ]
    assert len(botos) == 3
    assert botos[0].specifier == "==1.37.38"
    assert str(botos[0].marker) == 'python_full_version < "3.9"'
    assert botos[1].specifier == "==1.42.97"
    assert str(botos[1].marker) == 'python_full_version == "3.9.*"'
    assert botos[2].specifier == "==1.43.118"
    assert str(botos[2].marker) == (
        '(python_full_version >= "3.13" '
        'or (python_full_version >= "3.11" and python_full_version < "3.13")) '
        'or python_full_version == "3.10.*"'
    )

    assert (
        'colorama==0.4.6; sys_platform == "win32"'
        in dst_metadata["optional-dependencies"]["pinned"]
    )
    assert (
        'importlib-resources==6.5.2; python_version < "3.10" and python_full_version == "3.9.*"'
        in dst_metadata["optional-dependencies"]["pinned"]
    )


def test_update_metadata_no_optional_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    metadata: dict[str, Any] = {
        "dependencies": [
            "anyio>=4.5.2",
            "boto3>=1.36.15",
            "colorama; sys_platform == 'win32'",
            "exceptiongroup>=1.2.2",
            "importlib-resources; python_version < '3.10'",
            "fastapi>=0.115.8",
        ],
    }
    hook = PinnedExtraMetadataHook("fixtures/lockfiles/project", {"extra-name": "pinned"})

    dst_metadata = deepcopy(metadata)
    hook.update(dst_metadata)

    assert dst_metadata["dependencies"] == metadata["dependencies"]

    botos = [
        Requirement(dep)
        for dep in dst_metadata["optional-dependencies"]["pinned"]
        if dep.startswith("boto3")
    ]
    assert len(botos) == 3
    assert botos[0].specifier == "==1.37.38"
    assert str(botos[0].marker) == 'python_full_version < "3.9"'
    assert botos[1].specifier == "==1.42.97"
    assert str(botos[1].marker) == 'python_full_version == "3.9.*"'
    assert botos[2].specifier == "==1.43.118"
    assert str(botos[2].marker) == (
        '(python_full_version >= "3.13" '
        'or (python_full_version >= "3.11" and python_full_version < "3.13")) '
        'or python_full_version == "3.10.*"'
    )
    assert (
        'colorama==0.4.6; sys_platform == "win32"'
        in dst_metadata["optional-dependencies"]["pinned"]
    )
    assert (
        'importlib-resources==6.5.2; python_version < "3.10" and python_full_version == "3.9.*"'
        in dst_metadata["optional-dependencies"]["pinned"]
    )


def test_plugin_disabled_without_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the plugin does nothing when HATCH_PINNED_EXTRA_ENABLE is not set."""
    monkeypatch.delenv("HATCH_PINNED_EXTRA_ENABLE", raising=False)
    metadata: dict[str, Any] = {
        "dependencies": [
            "anyio>=4.5.2",
            "boto3>=1.36.15",
        ],
    }
    hook = PinnedExtraMetadataHook("fixtures/lockfiles/project", {"extra-name": "pinned"})

    dst_metadata = deepcopy(metadata)
    with pytest.warns(
        UserWarning,
        match="HATCH_PINNED_EXTRA_ENABLE is not set, pinned extra is disabled",
    ):
        hook.update(dst_metadata)

    # Metadata should be unchanged when env var is not set
    assert dst_metadata == metadata
    assert "optional-dependencies" not in dst_metadata


@pytest.mark.parametrize("env_var", ["0", "false", "no", "off"])
def test_plugin_disabled_with_false_env_var(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Test that the plugin does nothing when HATCH_PINNED_EXTRA_ENABLE is set to a false value."""
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", env_var)
    metadata: dict[str, Any] = {
        "dependencies": [
            "anyio>=4.5.2",
            "boto3>=1.36.15",
        ],
    }
    hook = PinnedExtraMetadataHook("fixtures/lockfiles/project", {"extra-name": "pinned"})

    dst_metadata = deepcopy(metadata)
    with pytest.warns(
        UserWarning,
        match="HATCH_PINNED_EXTRA_ENABLE is not set, pinned extra is disabled",
    ):
        hook.update(dst_metadata)

    # Metadata should be unchanged when env var is false
    assert dst_metadata == metadata
    assert "optional-dependencies" not in dst_metadata


@pytest.mark.parametrize("env_var", ["1", "true", "yes", "on"])
def test_plugin_enabled_with_env_var(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Test that the plugin works when HATCH_PINNED_EXTRA_ENABLE is set."""
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", env_var)
    metadata: dict[str, Any] = {
        "dependencies": [
            "anyio>=4.5.2",
            "boto3>=1.36.15",
        ],
    }
    hook = PinnedExtraMetadataHook("fixtures/lockfiles/project", {"extra-name": "pinned"})

    dst_metadata = deepcopy(metadata)
    hook.update(dst_metadata)

    # Metadata should be updated when env var is set
    assert dst_metadata != metadata
    assert "optional-dependencies" in dst_metadata
    assert "pinned" in dst_metadata["optional-dependencies"]
    botos = [
        Requirement(dep)
        for dep in dst_metadata["optional-dependencies"]["pinned"]
        if dep.startswith("boto3")
    ]
    assert len(botos) == 3
    assert botos[0].specifier == "==1.37.38"
    assert str(botos[0].marker) == 'python_full_version < "3.9"'
    assert botos[1].specifier == "==1.42.97"
    assert str(botos[1].marker) == 'python_full_version == "3.9.*"'
    assert botos[2].specifier == "==1.43.118"
    assert str(botos[2].marker) == (
        '(python_full_version >= "3.13" '
        'or (python_full_version >= "3.11" and python_full_version < "3.13")) '
        'or python_full_version == "3.10.*"'
    )


def test_invalid_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the plugin does nothing when HATCH_PINNED_EXTRA_ENABLE is set to an invalid value."""  # ruff:ignore[line-too-long]
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "invalid")
    metadata: dict[str, Any] = {
        "dependencies": [
            "anyio>=4.5.2",
            "boto3>=1.36.15",
        ],
    }
    hook = PinnedExtraMetadataHook("fixtures/lockfiles/project", {"extra-name": "pinned"})
    with pytest.raises(ValueError, match="invalid truth value 'invalid'"):
        hook.update(metadata)


def test_same_version_with_different_markers_is_sortable() -> None:
    """Pins that differ only by marker (including no marker) must not be compared as `Marker`s."""
    lock = {
        "package": [
            {"name": "app", "version": "0.1.0", "source": {"virtual": "."}},
            {
                "name": "a",
                "version": "1.0",
                "dependencies": [{"name": "shared", "marker": "sys_platform == 'linux'"}],
            },
            {
                "name": "b",
                "version": "1.0",
                "dependencies": [{"name": "shared", "marker": "sys_platform == 'win32'"}],
            },
            {"name": "c", "version": "1.0", "dependencies": [{"name": "shared"}]},
            {"name": "shared", "version": "1.0"},
        ],
    }

    reqs = parse_pinned_deps_from_uv_lock(lock, dependencies=["a", "b", "c"])

    assert [(r.name, str(r.marker) if r.marker else None) for r in reqs] == [
        ("a", None),
        ("b", None),
        ("c", None),
        ("shared", None),
        ("shared", 'sys_platform == "linux"'),
        ("shared", 'sys_platform == "win32"'),
    ]


@pytest.mark.xfail(
    strict=True,
    reason="workspace members are skipped as editable, along with their dependencies",
)
def test_workspace_member_dependencies_are_included() -> None:
    """Dependencies of a uv workspace member must be pinned for the packages that use it."""
    lock = read_toml(Path("fixtures/lockfiles/workspace/uv.lock"))

    reqs = parse_pinned_deps_from_uv_lock(
        lock,
        dependencies=["workspace-lib", "typing-extensions>=4"],
    )

    assert {req.name for req in reqs} >= {"idna", "typing-extensions"}


def test_extras_of_every_locked_version_are_resolved() -> None:
    """Each fork of a package can pull different packages through the same extra."""
    lock = read_toml(Path("fixtures/lockfiles/forked_extras/uv.lock"))

    reqs = parse_pinned_deps_from_uv_lock(lock, dependencies=["lib[feature]"])

    assert {req.name for req in reqs} == {"lib", "new-helper", "old-helper"}


def test_extra_reached_through_different_platform_markers() -> None:
    """A shared extra must stay installable on every platform that reaches it."""
    lock = read_toml(Path("fixtures/lockfiles/platform_extras/uv.lock"))

    reqs = parse_pinned_deps_from_uv_lock(lock, dependencies=["app"])

    def _satisfied_names(reqs: list[Any], env: dict[str, str]) -> set[str]:
        """Names of the pins whose marker (if any) holds in the given environment."""
        return {req.name for req in reqs if req.marker is None or req.marker.evaluate(env)}

    assert "extra-dep" in _satisfied_names(reqs, {"sys_platform": "win32"})
    assert "extra-dep" in _satisfied_names(reqs, {"sys_platform": "darwin"})
    assert "extra-dep" not in _satisfied_names(reqs, {"sys_platform": "linux"})


@pytest.mark.xfail(
    strict=True,
    raises=KeyError,
    reason="`metadata['dependencies']` is accessed unconditionally",
)
def test_update_metadata_without_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    """A project with no `dependencies` should not make the hook crash."""
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    hook = PinnedExtraMetadataHook("fixtures/lockfiles/no_deps", {"extra-name": "pinned"})

    metadata: dict[str, Any] = {}
    hook.update(metadata)

    assert metadata.get("optional-dependencies", {}).get("pinned", []) == []

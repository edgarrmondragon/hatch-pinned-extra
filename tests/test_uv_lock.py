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

    assert reqs[1].name == "anyio"
    assert reqs[1].version == Version("4.5.2")
    assert str(reqs[1].marker) == 'python_full_version < "3.9"'

    assert reqs[2].name == "anyio"
    assert reqs[2].version == Version("4.12.1")
    assert str(reqs[2].marker) == 'python_full_version == "3.9.*"'

    assert reqs[3].name == "anyio"
    assert reqs[3].version == Version("4.13.0")
    assert str(reqs[3].marker) == (
        'python_full_version >= "3.13" '
        'or (python_full_version >= "3.10" and python_full_version < "3.13")'
    )

    assert reqs[4].name == "exceptiongroup"


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
    assert len(botos) == 2
    assert botos[0].specifier == "==1.37.38"
    assert str(botos[0].marker) == 'python_full_version < "3.9"'
    assert botos[1].specifier == "==1.42.88"
    assert str(botos[1].marker) == (
        '(python_full_version >= "3.13" '
        'or (python_full_version >= "3.10" and python_full_version < "3.13")) '
        'or python_full_version == "3.9.*"'
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
    assert len(botos) == 2
    assert botos[0].specifier == "==1.37.38"
    assert str(botos[0].marker) == 'python_full_version < "3.9"'
    assert botos[1].specifier == "==1.42.88"
    assert str(botos[1].marker) == (
        '(python_full_version >= "3.13" '
        'or (python_full_version >= "3.10" and python_full_version < "3.13")) '
        'or python_full_version == "3.9.*"'
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
    assert len(botos) == 2
    assert botos[0].specifier == "==1.37.38"
    assert str(botos[0].marker) == 'python_full_version < "3.9"'
    assert botos[1].specifier == "==1.42.88"
    assert str(botos[1].marker) == (
        '(python_full_version >= "3.13" '
        'or (python_full_version >= "3.10" and python_full_version < "3.13")) '
        'or python_full_version == "3.9.*"'
    )


def test_invalid_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the plugin does nothing when HATCH_PINNED_EXTRA_ENABLE is set to an invalid value."""  # noqa: E501
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

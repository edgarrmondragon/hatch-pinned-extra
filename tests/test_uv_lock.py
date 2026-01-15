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

import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from packaging.requirements import Requirement

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from hatch_pinned_extra import PinnedExtraMetadataHook, parse_pinned_deps_from_uv_lock


def test_missing_uv_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    hook = PinnedExtraMetadataHook(str(tmp_path), {"extra-name": "pinned"})
    with pytest.warns(
        UserWarning,
        match="uv.lock file not found in",
    ):
        hook.update({})


def test_parse_pinned_deps_from_uv_lock() -> None:
    with open("fixtures/project/uv.lock", "rb") as f:
        lock = tomllib.load(f)

    reqs = parse_pinned_deps_from_uv_lock(
        lock,
        dependencies=["annotated-types", "anyio"],
    )
    assert reqs[0].name == "annotated-types"
    assert reqs[0].specifier == "==0.7.0"

    assert reqs[1].name == "anyio"
    assert reqs[1].specifier == "==4.5.2"
    assert str(reqs[1].marker) == 'python_full_version < "3.9"'

    reqs = parse_pinned_deps_from_uv_lock(
        lock,
        dependencies=["anyio"],
    )
    assert reqs[0].name == "anyio"
    assert reqs[0].specifier == "==4.5.2"
    assert str(reqs[0].marker) == 'python_full_version < "3.9"'

    assert reqs[1].name == "anyio"
    assert reqs[1].specifier == "==4.9.0"
    assert str(reqs[1].marker) == (
        'python_full_version >= "3.13" '
        'or (python_full_version >= "3.10" and python_full_version < "3.13") '
        'or python_full_version == "3.9.*"'
    )

    assert reqs[2].name == "exceptiongroup"


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
    hook = PinnedExtraMetadataHook("fixtures/project", {"extra-name": "pinned"})

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
    assert botos[1].specifier == "==1.38.36"
    assert str(botos[1].marker) == (
        'python_full_version >= "3.13" '
        'or (python_full_version >= "3.10" and python_full_version < "3.13") '
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
    hook = PinnedExtraMetadataHook("fixtures/project", {"extra-name": "pinned"})

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
    assert botos[1].specifier == "==1.38.36"
    assert str(botos[1].marker) == (
        'python_full_version >= "3.13" '
        'or (python_full_version >= "3.10" and python_full_version < "3.13") '
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


def test_plugin_disabled_without_env_var() -> None:
    """Test that the plugin does nothing when HATCH_PINNED_EXTRA_ENABLE is not set."""
    metadata: dict[str, Any] = {
        "dependencies": [
            "anyio>=4.5.2",
            "boto3>=1.36.15",
        ],
    }
    hook = PinnedExtraMetadataHook("fixtures/project", {"extra-name": "pinned"})

    dst_metadata = deepcopy(metadata)
    with pytest.warns(
        UserWarning,
        match="HATCH_PINNED_EXTRA_ENABLE is not set, pinned extra is disabled",
    ):
        hook.update(dst_metadata)

    # Metadata should be unchanged when env var is not set
    assert dst_metadata == metadata
    assert "optional-dependencies" not in dst_metadata


def test_plugin_enabled_with_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the plugin works when HATCH_PINNED_EXTRA_ENABLE is set."""
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    metadata: dict[str, Any] = {
        "dependencies": [
            "anyio>=4.5.2",
            "boto3>=1.36.15",
        ],
    }
    hook = PinnedExtraMetadataHook("fixtures/project", {"extra-name": "pinned"})

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
    assert botos[1].specifier == "==1.38.36"
    assert str(botos[1].marker) == (
        'python_full_version >= "3.13" '
        'or (python_full_version >= "3.10" and python_full_version < "3.13") '
        'or python_full_version == "3.9.*"'
    )


def test_recursive_extras_resolution() -> None:
    """Test that all dependencies from fastapi[standard] and its recursive extras are included."""
    with open("fixtures/extras/uv.lock", "rb") as f:
        lock = tomllib.load(f)

    # This matches the dependency in fixtures/extras/pyproject.toml
    reqs = parse_pinned_deps_from_uv_lock(
        lock,
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
        "sniffio",
        "anyio",
        "exceptiongroup",
        "markdown-it-py",
        "mdurl",
        "pygments",
        "shellingham",
        "markupsafe",
    }
    # Check that all expected dependencies are present
    missing = expected - names
    assert not missing, f"Missing dependencies in pinned output: {missing}"

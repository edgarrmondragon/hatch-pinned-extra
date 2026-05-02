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

import os
import shutil
from importlib.metadata import entry_points
from pathlib import Path

import pytest

from hatch_pinned_extra import PinnedExtraMetadataHook
from hatch_pinned_extra._compat import read_toml


def test_entry_point_is_loadable() -> None:
    (ep,) = entry_points(group="hatch", name="pinned_extra")
    plugin = ep.load()
    assert hasattr(plugin, "hatch_register_metadata_hook")


def test_missing_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    hook = PinnedExtraMetadataHook(str(tmp_path), {"extra-name": "pinned"})
    with pytest.warns(UserWarning, match=r"was not found .* Skipping generation"):
        hook.update({})


def test_invalid_file_type(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    lockfile = "not-a-valid-lock.toml"
    tmp_path.joinpath(lockfile).touch()
    hook = PinnedExtraMetadataHook(
        str(tmp_path),
        {"extra-name": "pinned", "lockfile": lockfile},
    )
    with pytest.warns(UserWarning, match=r"neither uv.lock .* Skipping generation"):
        hook.update({})


def test_uv_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    project_path = Path("fixtures/lockfiles/project")
    tmp_project_path = tmp_path / "project"

    shutil.copytree(project_path, tmp_project_path)

    hook = PinnedExtraMetadataHook(str(tmp_project_path), {"extra-name": "pinned"})
    pyproject = read_toml(tmp_project_path / "pyproject.toml")
    metadata = {"dependencies": pyproject["project"]["dependencies"]}
    hook.update(metadata)

    assert metadata["optional-dependencies"] == {
        "pinned": [
            "annotated-doc==0.0.4",
            "annotated-types==0.7.0",
            'anyio==4.5.2; python_full_version < "3.9"',
            'anyio==4.12.1; python_full_version == "3.9.*"',
            'anyio==4.13.0; python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")',  # noqa: E501
            'boto3==1.37.38; python_full_version < "3.9"',
            'boto3==1.42.88; (python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")) or python_full_version == "3.9.*"',  # noqa: E501
            'botocore==1.37.38; python_full_version < "3.9"',
            'botocore==1.42.88; (python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")) or python_full_version == "3.9.*"',  # noqa: E501
            'colorama==0.4.6; sys_platform == "win32"',
            "exceptiongroup==1.3.1",
            'fastapi==0.124.4; python_full_version < "3.9"',
            'fastapi==0.128.8; python_full_version == "3.9.*"',
            'fastapi==0.135.3; python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")',  # noqa: E501
            "idna==3.11",
            'importlib-resources==6.4.5; python_version < "3.10" and python_full_version < "3.9"',
            'importlib-resources==6.5.2; python_version < "3.10" and python_full_version == "3.9.*"',  # noqa: E501
            'jmespath==1.0.1; python_full_version < "3.9"',
            'jmespath==1.1.0; (python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")) or python_full_version == "3.9.*"',  # noqa: E501
            'pydantic==2.10.6; python_full_version < "3.9"',
            'pydantic==2.12.5; (python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")) or python_full_version == "3.9.*"',  # noqa: E501
            'pydantic-core==2.27.2; python_full_version < "3.9"',
            'pydantic-core==2.41.5; (python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")) or python_full_version == "3.9.*"',  # noqa: E501
            "python-dateutil==2.9.0.post0",
            's3transfer==0.11.5; python_full_version < "3.9"',
            's3transfer==0.16.0; (python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")) or python_full_version == "3.9.*"',  # noqa: E501
            "six==1.17.0",
            "sniffio==1.3.1",
            'starlette==0.44.0; python_full_version < "3.9"',
            'starlette==0.49.3; python_full_version == "3.9.*"',
            'starlette==1.0.0; python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")',  # noqa: E501
            'typing-extensions==4.13.2; python_full_version < "3.9"',
            'typing-extensions==4.15.0; (python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")) or python_full_version == "3.9.*"',  # noqa: E501
            "typing-inspection==0.4.2",
            'urllib3==1.26.20; python_full_version == "3.9.*" or python_full_version < "3.9"',
            'urllib3==2.6.3; python_full_version >= "3.13" or (python_full_version >= "3.10" and python_full_version < "3.13")',  # noqa: E501
            'zipp==3.20.2; python_version < "3.10" and python_full_version < "3.9"',
            'zipp==3.23.0; python_version < "3.10" and python_full_version == "3.9.*"',
        ]
    }


def test_pylock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    project_path = Path("fixtures/lockfiles/project")
    tmp_project_path = tmp_path / "project"

    shutil.copytree(project_path, tmp_project_path)
    os.remove(tmp_project_path / "uv.lock")

    hook = PinnedExtraMetadataHook(
        str(tmp_project_path),
        {"extra-name": "pinned", "lockfile": "pylock.uv.toml"},
    )
    pyproject = read_toml(tmp_project_path / "pyproject.toml")
    metadata = {"dependencies": pyproject["project"]["dependencies"]}
    hook.update(metadata)

    assert metadata["optional-dependencies"] == {
        "pinned": [
            'anyio==4.5.2; python_full_version < "3.9"',
            'anyio==4.12.1; python_full_version == "3.9.*"',
            'anyio==4.13.0; python_full_version >= "3.10"',
            'boto3==1.37.38; python_full_version < "3.9"',
            'boto3==1.42.88; python_full_version >= "3.9"',
            'colorama==0.4.6; sys_platform == "win32" and sys_platform == "win32"',
            "exceptiongroup==1.3.1",
            'fastapi==0.124.4; python_full_version < "3.9"',
            'fastapi==0.128.8; python_full_version == "3.9.*"',
            'fastapi==0.135.3; python_full_version >= "3.10"',
            'importlib-resources==6.4.5; python_version < "3.10" and python_full_version < "3.9"',
            'importlib-resources==6.5.2; python_version < "3.10" and python_full_version == "3.9.*"',  # noqa: E501
        ]
    }

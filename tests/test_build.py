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

from __future__ import annotations

import warnings
import zipfile
from typing import TYPE_CHECKING

import pytest
from packaging.metadata import parse_email
from pyproject_hooks import BuildBackendHookCaller, BuildBackendWarning

from hatch_pinned_extra._compat import read_toml

if TYPE_CHECKING:
    from pathlib import Path

    from packaging.metadata import RawMetadata


def _metadata(wheel_path: Path) -> RawMetadata:
    name, version, *_ = wheel_path.name.split("-", 2)
    metadata = f"{name}-{version}.dist-info/METADATA"  # e.g. project-0.1.0.dist-info/METADATA

    with zipfile.ZipFile(wheel_path, "r") as zip:
        meta, _ = parse_email(zip.read(metadata))

    return meta


@pytest.mark.parametrize(
    "location",
    [
        "extras",
        "project",
        "requests",
    ],
)
def test_hook(
    pytestconfig: pytest.Config,
    location: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    subtests: pytest.Subtests,
) -> None:
    project_path = pytestconfig.rootpath / f"fixtures/lockfiles/{location}"
    toml_data = read_toml(project_path / "pyproject.toml")

    hooks = BuildBackendHookCaller(
        project_path.as_posix(),
        toml_data["build-system"]["build-backend"],
    )

    with subtests.test("disabled"):
        wheel_dir = tmp_path / "disabled"
        with pytest.warns(
            BuildBackendWarning,
            match=r"HATCH_PINNED_EXTRA_ENABLE is not set, pinned extra is disabled",
        ):
            wheel = hooks.build_wheel(wheel_directory=wheel_dir.as_posix())

        meta = _metadata(wheel_dir / wheel)
        assert "provides_extra" not in meta
        assert not any("extra == 'pinned'" in requirement for requirement in meta["requires_dist"])

    with subtests.test("enabled"):
        wheel_dir = tmp_path / "enabled"
        with warnings.catch_warnings(), monkeypatch.context() as m:
            warnings.simplefilter("error")
            m.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
            wheel = hooks.build_wheel(wheel_directory=wheel_dir.as_posix())

        meta = _metadata(wheel_dir / wheel)
        assert meta["provides_extra"] == ["pinned"]
        assert any("extra == 'pinned'" in requirement for requirement in meta["requires_dist"])

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
from collections import defaultdict
from typing import TYPE_CHECKING

import pytest
from packaging.metadata import parse_email
from packaging.requirements import Requirement
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


def test_build_multiple_extras(
    pytestconfig: pytest.Config,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    subtests: pytest.Subtests,
) -> None:
    project_path = pytestconfig.rootpath / "fixtures/lockfiles/multiple"
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
        assert meta["provides_extra"] == ["recommended"]

        opt = [req for req in meta["requires_dist"] if "extra == 'recommended'" in req]
        assert opt == ["requests-cache>=1.1; extra == 'recommended'"]

    with subtests.test("enabled"):
        wheel_dir = tmp_path / "enabled"
        with warnings.catch_warnings(), monkeypatch.context() as m:
            warnings.simplefilter("error")
            m.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
            wheel = hooks.build_wheel(wheel_directory=wheel_dir.as_posix())

        meta = _metadata(wheel_dir / wheel)
        assert meta["provides_extra"] == [
            "pinned",
            "pinned-recommended",  # TODO: check if extra names should be normalized or not
            "recommended",
        ]

        opt_dict: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for rs in meta["requires_dist"]:
            req = Requirement(rs)
            if req.marker is None:
                continue

            opt_dict[str(req.marker)].append((req.name, str(req.specifier)))

        assert opt_dict['extra == "recommended"'] == [("requests-cache", ">=1.1")]
        assert opt_dict['extra == "pinned"'] == [
            ("certifi", "==2026.10.23"),
            ("charset-normalizer", "==3.5.2"),
            ("idna", "==3.20"),
            ("requests", "==2.34.2"),
            ("urllib3", "==2.8.0"),
        ]
        assert opt_dict['extra == "pinned-recommended"'] == [
            ("attrs", "==26.1.0"),
            ("cattrs", "==26.2.1"),
            ("certifi", "==2026.10.23"),
            ("charset-normalizer", "==3.5.2"),
            ("idna", "==3.20"),
            ("platformdirs", "==4.14.5"),
            ("requests-cache", "==1.3.3"),
            ("requests", "==2.34.2"),
            ("typing-extensions", "==4.16.0"),
            ("url-normalize", "==3.1.0"),
            ("urllib3", "==2.8.0"),
        ]


@pytest.mark.parametrize(
    ("location", "pinned"),
    [
        # Runs after the hook providing `dependencies`, so it pins those
        ("dynamic_deps_pinned_last", {"typing-extensions"}),
        # Runs before it, so `dependencies` is not set yet and the lockfile's are used
        ("dynamic_deps_pinned_first", {"idna"}),
    ],
)
def test_hook_order_with_dynamic_dependencies(
    pytestconfig: pytest.Config,
    location: str,
    pinned: set[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hatchling runs metadata hooks in the order of their tables in `pyproject.toml`."""
    project_path = pytestconfig.rootpath / f"fixtures/lockfiles/{location}"
    toml_data = read_toml(project_path / "pyproject.toml")

    hooks = BuildBackendHookCaller(
        project_path.as_posix(),
        toml_data["build-system"]["build-backend"],
    )

    with warnings.catch_warnings(), monkeypatch.context() as m:
        warnings.simplefilter("error")
        m.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
        wheel = hooks.build_wheel(wheel_directory=tmp_path.as_posix())

    meta = _metadata(tmp_path / wheel)
    assert meta["requires_dist"][0] == "typing-extensions>=4"
    assert {
        Requirement(requirement).name
        for requirement in meta["requires_dist"]
        if "extra == 'pinned'" in requirement
    } == pinned

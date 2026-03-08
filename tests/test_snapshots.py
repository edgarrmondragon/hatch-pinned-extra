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

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from packaging.markers import Marker
from packaging.metadata import Metadata
from packaging.requirements import Requirement

from hatch_pinned_extra import PinnedExtraMetadataHook
from hatch_pinned_extra._compat import read_toml

if TYPE_CHECKING:
    from packaging.metadata import RawMetadata
    from syrupy.assertion import SnapshotAssertion


def _to_raw_metadata(
    *,
    name: str,
    version: str,
    metadata: dict[str, Any],
) -> RawMetadata:
    """Convert a hatch metadata dict to a packaging RawMetadata dict.

    Maps ``dependencies`` to ``requires_dist`` and ``optional-dependencies``
    to ``provides_extra`` plus additional ``requires_dist`` entries with the
    appropriate ``extra == "..."`` marker, mirroring what ends up in a wheel's
    METADATA file.
    """
    requires_dist: list[str] = list(metadata.get("dependencies", []))
    provides_extra: list[str] = []

    for extra_name, extra_deps in metadata.get("optional-dependencies", {}).items():
        provides_extra.append(extra_name)
        for dep in extra_deps:
            req = Requirement(dep)
            extra_marker = f'extra == "{extra_name}"'
            combined = extra_marker if req.marker is None else f"({req.marker}) and {extra_marker}"
            req.marker = Marker(combined)
            requires_dist.append(str(req))

    return {
        "metadata_version": "2.3",
        "name": name,
        "version": version,
        "requires_dist": requires_dist,
        "provides_extra": provides_extra,
    }


@pytest.mark.parametrize(
    "lockfile",
    ["uv.lock", "pylock.uv.toml", "pylock.pip.toml"],
)
def test_snapshot_project_metadata(
    monkeypatch: pytest.MonkeyPatch, snapshot: SnapshotAssertion, lockfile: str
) -> None:
    """Snapshot the METADATA content for the lockfiles/project fixture."""
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")

    pyproject = read_toml(Path("fixtures/lockfiles/project/pyproject.toml"))
    metadata: dict[str, Any] = {
        "dependencies": pyproject["project"]["dependencies"],
        "optional-dependencies": pyproject["project"]["optional-dependencies"],
    }
    hook = PinnedExtraMetadataHook(
        "fixtures/lockfiles/project",
        {"extra-name": "pinned", "lockfile": lockfile},
    )

    dst = deepcopy(metadata)
    hook.update(dst)

    raw = _to_raw_metadata(name="project", version="0.1.0", metadata=dst)
    wheel_metadata = Metadata.from_raw(raw)
    assert wheel_metadata.as_rfc822().as_string() == snapshot


@pytest.mark.parametrize(
    "lockfile",
    ["uv.lock", "pylock.uv.toml", "pylock.pip.toml"],
)
def test_snapshot_extras_metadata(
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
    lockfile: str,
) -> None:
    """Snapshot the METADATA content for the lockfiles/extras fixture."""
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")

    pyproject = read_toml(Path("fixtures/lockfiles/extras/pyproject.toml"))
    metadata: dict[str, Any] = {
        "dependencies": pyproject["project"]["dependencies"],
    }
    hook = PinnedExtraMetadataHook(
        "fixtures/lockfiles/extras",
        {"extra-name": "pinned", "lockfile": lockfile},
    )

    dst = deepcopy(metadata)
    hook.update(dst)

    raw = _to_raw_metadata(name="dep-with-extras", version="0.1.0", metadata=dst)
    wheel_metadata = Metadata.from_raw(raw)
    assert wheel_metadata.as_rfc822().as_string() == snapshot


@pytest.mark.parametrize(
    "lockfile",
    ["uv.lock", "pylock.uv.toml", "pylock.pip.toml"],
)
def test_snapshot_requests_metadata(
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
    lockfile: str,
) -> None:
    """Snapshot the METADATA content for the lockfiles/extras fixture."""
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    metadata: dict[str, Any] = {
        "dependencies": [
            "requests~=2.32",
            "requests-cache~=1.2",
        ],
    }

    hook = PinnedExtraMetadataHook(
        "fixtures/lockfiles/requests",
        {"extra-name": "pinned", "lockfile": lockfile},
    )

    dst = deepcopy(metadata)
    hook.update(dst)

    raw = _to_raw_metadata(name="requests", version="0.1.0", metadata=dst)
    wheel_metadata = Metadata.from_raw(raw)
    assert wheel_metadata.as_rfc822().as_string() == snapshot

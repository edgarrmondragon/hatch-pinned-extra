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
from typing import TYPE_CHECKING, Any

import packaging
import pytest
from packaging.markers import Marker
from packaging.metadata import Metadata
from packaging.requirements import Requirement
from packaging.version import Version

from hatch_pinned_extra import PinnedExtraMetadataHook

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


@pytest.mark.skipif(
    Version(packaging.__version__) < Version("26.0"),
    reason="packaging < 26.0 does not support writing METADATA files",
)
def test_snapshot_project_metadata(
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Snapshot the METADATA content for the uv_lock/project fixture."""
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
    hook = PinnedExtraMetadataHook("fixtures/uv_lock/project", {"extra-name": "pinned"})

    dst = deepcopy(metadata)
    hook.update(dst)

    raw = _to_raw_metadata(name="project", version="0.1.0", metadata=dst)
    wheel_metadata = Metadata.from_raw(raw)
    assert wheel_metadata.as_rfc822().as_string() == snapshot


@pytest.mark.skipif(
    Version(packaging.__version__) < Version("26.0"),
    reason="packaging < 26.0 does not support writing METADATA files",
)
def test_snapshot_extras_metadata(
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Snapshot the METADATA content for the uv_lock/extras fixture."""
    monkeypatch.setenv("HATCH_PINNED_EXTRA_ENABLE", "1")
    metadata: dict[str, Any] = {
        "dependencies": [
            "fastapi[standard]>=0.115.12",
        ],
    }
    hook = PinnedExtraMetadataHook("fixtures/uv_lock/extras", {"extra-name": "pinned"})

    dst = deepcopy(metadata)
    hook.update(dst)

    raw = _to_raw_metadata(name="dep-with-extras", version="0.1.0", metadata=dst)
    wheel_metadata = Metadata.from_raw(raw)
    assert wheel_metadata.as_rfc822().as_string() == snapshot

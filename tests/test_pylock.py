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

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from hatch_pinned_extra._compat import read_toml
from hatch_pinned_extra._pylock import parse_pinned_deps_from_pylock

if TYPE_CHECKING:
    from hatch_pinned_extra._base import _PinnedRequirement


def _group_pins_by_package(reqs: list[_PinnedRequirement]) -> dict[str, dict[str, str | None]]:
    res: dict[str, dict[str, str | None]] = {}
    for req in reqs:
        if req.name not in res:
            res[req.name] = {}

        res[req.name][str(req.version)] = str(req.marker) if req.marker else None

    return res


@pytest.fixture
def lock() -> dict[str, Any]:
    return read_toml(Path("fixtures/lockfiles/project/pylock.uv.toml"))


def test_parse_pinned_deps_from_pylock(lock: dict[str, Any]) -> None:
    reqs = parse_pinned_deps_from_pylock(lock)
    by_package = _group_pins_by_package(reqs)
    assert by_package["annotated-doc"] == {
        "0.0.4": 'python_full_version < "3.9"',
        "0.0.5": 'python_full_version == "3.9.*"',
        "0.0.6": 'python_full_version == "3.10.*"',
        "0.0.7": 'python_full_version >= "3.11"',
    }

    assert by_package["annotated-types"] == {
        "0.7.0": 'python_full_version < "3.10"',
        "0.8.0": 'python_full_version >= "3.10"',
    }

    assert by_package["anyio"] == {
        "4.5.2": 'python_full_version < "3.9"',
        "4.12.1": 'python_full_version == "3.9.*"',
        "4.16.0": 'python_full_version >= "3.10"',
    }

    # uv does not export transitive dependency information to pylock.toml
    assert len(set(r.name for r in reqs)) == 23

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

from pathlib import Path
from typing import Any

import pytest
from packaging.version import Version

from hatch_pinned_extra._compat import read_toml
from hatch_pinned_extra._pylock import parse_pinned_deps_from_pylock


@pytest.fixture
def uv_lock() -> dict[str, Any]:
    return read_toml(Path("fixtures/lockfiles/project/pylock.uv.toml"))


def test_parse_pinned_deps_from_pylock(uv_lock: dict[str, Any]) -> None:
    reqs = parse_pinned_deps_from_pylock(uv_lock, dependencies=["annotated-types", "anyio"])
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
    assert str(reqs[3].marker) == 'python_full_version >= "3.10"'

    # uv does not export transitive dependency information to pylock.toml
    assert len(set(r.name for r in reqs)) == 2

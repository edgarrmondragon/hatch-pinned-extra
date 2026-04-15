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

import re
from dataclasses import dataclass
from functools import reduce
from operator import and_
from typing import TYPE_CHECKING

from packaging.markers import Marker

if TYPE_CHECKING:
    from packaging.version import Version

# Marker variables that are platform-specific (not Python-version selectors).
# https://packaging.python.org/en/latest/specifications/dependency-specifiers/#environment-markers
_PLATFORM_MARKER_RE = re.compile(
    r"\b(?:sys_platform|os_name|platform_machine|platform_system"
    r"|platform_release|platform_version|platform_python_implementation"
    r"|implementation_name)\b"
)


@dataclass(order=True)
class _PinnedRequirement:
    name: str
    version: Version
    marker: Marker | None = None

    def __hash__(self) -> int:
        return hash((self.name, self.version, self.marker))

    def __str__(self) -> str:
        return f"{self.name}=={self.version}" + (f"; {self.marker}" if self.marker else "")


def _platform_only_marker(marker_str: str) -> Marker | None:
    """Return only the platform-specific conditions from a dep marker.

    In uv.lock, dep markers combine two kinds of conditions:

    - **Python-version selectors** (e.g. ``python_full_version < "3.10"``):
      these pick which lock-file entry of the dependency to use.  The dep
      package's own ``resolution-markers`` already encode the same information,
      so re-propagating them only creates redundant / impossible marker
      combinations further down the dependency tree.
    - **Platform conditions** (``sys_platform``, ``platform_python_implementation``,
      …): genuine install-time guards that must be forwarded so that transitive
      deps (e.g. ``uvloop``) are not installed unconditionally.

    Dep markers in lock files are flat conjunctions, so splitting on
    ``" and "`` is safe.
    """
    terms = [t.strip() for t in marker_str.split(" and ")]
    platform_terms = [Marker(t) for t in terms if t and _PLATFORM_MARKER_RE.search(t)]
    if platform_terms:
        return reduce(and_, platform_terms)

    return None

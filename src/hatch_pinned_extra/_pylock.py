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

from typing import TYPE_CHECKING, Any, TypeAlias

from packaging.markers import Marker
from packaging.pylock import Package, Pylock
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from ._base import _merge_markers, _PinnedRequirement

if TYPE_CHECKING:
    from collections.abc import Iterable

Deps: TypeAlias = dict[str, dict[str, Package]]


def _extract_pylock_requirements(
    deps: Deps,
    name: str,
    *markers: str,
) -> list[_PinnedRequirement]:
    reqs = []

    for version in deps.get(name, {}):
        req = _PinnedRequirement(name, Version(version))

        package = deps[name][version]

        package_markers = (str(package.marker),) if package.marker else ()
        if new_marker := _merge_markers(*markers, *package_markers, op="and"):
            req.marker = str(Marker(new_marker))

        reqs.append(req)

    return reqs


def parse_pinned_deps_from_pylock(
    lock: dict[str, Any],
    dependencies: Iterable[str],
) -> list[_PinnedRequirement]:
    """Parse the pinned dependencies from a pylock.toml file."""
    reqs = []
    pylock = Pylock.from_dict(lock)

    deps: Deps = {}
    # for package in lock.get("package", []):
    for package in pylock.packages:
        name = package.name
        deps.setdefault(name, {})
        deps[name][str(package.version)] = package

    for dep in dependencies:
        req = Requirement(dep)
        name = canonicalize_name(req.name)
        markers = (str(req.marker),) if req.marker else ()
        reqs.extend(
            _extract_pylock_requirements(
                deps,
                name,
                *markers,
            )
        )

    # Sort by name, version, and markers, and deduplicate the requirements
    return sorted(set(reqs))

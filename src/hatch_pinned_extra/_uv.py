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

import sys
from typing import TYPE_CHECKING, Any

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from ._base import _merge_markers, _PinnedRequirement, _platform_only_marker

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from collections.abc import Iterable

Deps: TypeAlias = dict[str, dict[str, dict[str, Any]]]


def _extract_uv_requirements(
    deps: Deps,
    name: str,
    *markers: str,
    extras: set[str],
    visited: set[tuple[str, str]],
) -> list[_PinnedRequirement]:
    reqs = []

    for version in deps.get(name, {}):
        req = _PinnedRequirement(canonicalize_name(name), Version(version))

        package = deps[name][version]

        resolution_markers = _merge_markers(*package.get("resolution-markers", []), op="or")
        if new_marker := _merge_markers(*markers, resolution_markers, op="and"):
            req.marker = str(Marker(new_marker))

        reqs.append(req)

        # Handle normal dependencies
        for dep in package.get("dependencies", []):
            effective = _platform_only_marker(dep.get("marker", ""))
            new_markers = (*markers, effective) if effective else markers
            dep_extras = set(dep.get("extra", []))
            reqs.extend(
                _extract_uv_requirements(
                    deps,
                    dep["name"],
                    *new_markers,
                    extras=dep_extras,
                    visited=visited,
                )
            )

        # Handle extras recursively
        opt_deps = package.get("optional-dependencies", {})
        for extra in extras:
            if (name, extra) in visited:
                continue
            visited.add((name, extra))
            for dep in opt_deps.get(extra, []):
                dep_name = dep["name"]
                dep_extras = set(dep.get("extra", []))
                effective = _platform_only_marker(dep.get("marker", ""))
                new_markers = (*markers, effective) if effective else markers
                reqs.extend(
                    _extract_uv_requirements(
                        deps,
                        dep_name,
                        *new_markers,
                        extras=dep_extras,
                        visited=visited,
                    )
                )

    return reqs


def parse_pinned_deps_from_uv_lock(
    lock: dict[str, Any],
    dependencies: Iterable[str],
) -> list[_PinnedRequirement]:
    """Parse the pinned dependencies from a uv.lock file."""
    reqs = []

    deps: Deps = {}
    for package in lock.get("package", []):
        # skip the main package
        if package.get("source", {}).get("virtual") or package.get("source", {}).get("editable"):
            continue

        name = package["name"]
        deps.setdefault(name, {})

        version = package.get("version")
        deps[name][version] = package

    for dep in dependencies:
        req = Requirement(dep)
        name = canonicalize_name(req.name)
        markers = (str(req.marker),) if req.marker else ()
        extras = set(req.extras)
        reqs.extend(_extract_uv_requirements(deps, name, *markers, extras=extras, visited=set()))

    # Sort by name, version, and markers, and deduplicate the requirements
    return sorted(set(reqs))

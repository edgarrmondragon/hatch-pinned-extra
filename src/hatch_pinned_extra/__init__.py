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

import os
import os.path
import sys
import warnings
from typing import TYPE_CHECKING

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from collections.abc import Iterable

Deps: TypeAlias = dict[str, dict[str, dict]]


def _merge_markers(*markers: str, op: str) -> str:
    # wrap the markers in parentheses if they are not already and join them with " and "
    return f" {op} ".join(f"({marker})" for marker in markers if marker)


def _extract_requirements(
    deps: Deps,
    name: str,
    *markers: str,
    extras: set[str] | None = None,
    visited: set | None = None,
) -> list[Requirement]:
    if extras is None:
        extras = set()
    if visited is None:
        visited = set()
    reqs = []

    for version in deps.get(name, {}):
        package = deps[name][version]

        req_string = f"{name}=={version}"

        resolution_markers = _merge_markers(*package.get("resolution-markers", []), op="or")
        if new_markers := _merge_markers(*markers, resolution_markers, op="and"):
            req_string += f" ; {new_markers}"

        req = Requirement(req_string)
        req.name = canonicalize_name(req.name)
        reqs.append(req)

        # Handle normal dependencies
        for dep in package.get("dependencies", []):
            new_markers = (*markers, dep["marker"]) if dep.get("marker") else markers
            dep_extras = set(dep.get("extra", []))
            reqs.extend(
                _extract_requirements(
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
                reqs.extend(
                    _extract_requirements(
                        deps,
                        dep_name,
                        *markers,
                        extras=dep_extras,
                        visited=visited,
                    )
                )

    return reqs


def parse_pinned_deps_from_uv_lock(
    lock: dict,
    dependencies: Iterable[str],
) -> list[Requirement]:
    """Parse the pinned dependencies from a uv.lock file."""
    reqs = []

    deps: dict[str, dict[str, dict]] = {}
    for package in lock.get("package", []):
        # skip the main package
        if package.get("source", {}).get("virtual") or package.get("source", {}).get("editable"):
            continue

        name = package["name"]
        if name not in deps:
            deps[name] = {}

        version = package.get("version")
        if version not in deps[name]:
            deps[name][version] = package

    for dep in dependencies:
        req = Requirement(dep)
        name = canonicalize_name(req.name)
        markers = (str(req.marker),) if req.marker else ()
        extras = set(req.extras)
        reqs.extend(_extract_requirements(deps, name, *markers, extras=extras, visited=set()))

    # Sort by name and version, and deduplicate the requirements
    return sorted(set(reqs), key=lambda req: (req.name, str(req.specifier)))


class PinnedExtraMetadataHook(MetadataHookInterface):
    """Hatch plugin that adds a packaging extra with pinned dependencies from a lock file."""

    PLUGIN_NAME = "pinned_extra"

    def update(self, metadata: dict) -> None:
        # Check if plugin is enabled via environment variable
        if not os.environ.get("HATCH_PINNED_EXTRA_ENABLE"):
            warnings.warn(
                "HATCH_PINNED_EXTRA_ENABLE is not set, pinned extra is disabled",
                UserWarning,
                stacklevel=1,
            )
            return

        extra_name = self.config.get("extra-name", "pinned")

        uv_lock_path = os.path.join(self.root, "uv.lock")
        if not os.path.exists(uv_lock_path):
            warnings.warn(
                f"uv.lock file not found in {self.root}. "
                f"Skipping the generation of the '{extra_name}' extra.",
                UserWarning,
                stacklevel=2,
            )
            return

        with open(os.path.join(self.root, "uv.lock"), "rb") as f:
            lock = tomllib.load(f)

        pinned_reqs = parse_pinned_deps_from_uv_lock(lock, metadata["dependencies"])

        # add the pinned dependencies to the project table
        if "optional-dependencies" not in metadata:
            metadata["optional-dependencies"] = {}

        metadata["optional-dependencies"][extra_name] = [str(req) for req in pinned_reqs]


@hookimpl
def hatch_register_metadata_hook() -> type[PinnedExtraMetadataHook]:
    return PinnedExtraMetadataHook

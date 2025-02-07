import sys
from typing import Dict, Iterable, TypeAlias

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


Deps: TypeAlias = Dict[str, Dict[str, Dict]]


def _extract_requirements(name: str, deps: Deps) -> list[Requirement]:
    reqs = []

    for version in deps[name]:
        package = deps[name][version]

        req_string = f"{name}=={version}"

        if markers := package.get("resolution-markers", []):
            req_string += f" ; {' and '.join(markers)}"

        req = Requirement(req_string)
        req.name = canonicalize_name(req.name)
        reqs.append(req)

        for dep in package.get("dependencies", []):
            reqs.extend(_extract_requirements(dep["name"], deps))

    return reqs


def parse_pinned_deps_from_uv_lock(
    lock: dict,
    dependencies: Iterable[str],
) -> list[Requirement]:
    reqs = []

    deps: dict[str, dict[str, dict]] = {}
    for package in lock.get("package", []):
        # skip the main package
        if package.get("source", {}).get("virtual") or package.get("source", {}).get(
            "editable"
        ):
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

        reqs.extend(_extract_requirements(name, deps))

    # Sort by name and version, and deduplicate the requirements
    return sorted(set(reqs), key=lambda req: (req.name, str(req.specifier)))


class PinnedExtraMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "pinned_extra"

    def update(self, metadata: dict):
        extra_name = self.config.get("extra-name", "pinned")

        with open(f"{self.root}/uv.lock", "rb") as f:
            lock = tomllib.load(f)

        pinned_reqs = parse_pinned_deps_from_uv_lock(lock, metadata["dependencies"])

        # add the pinned dependencies to the project table
        metadata["optional-dependencies"] = {
            extra_name: [str(req) for req in pinned_reqs]
        }


@hookimpl
def hatch_register_metadata_hook() -> type[PinnedExtraMetadataHook]:
    return PinnedExtraMetadataHook

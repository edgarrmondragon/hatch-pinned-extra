import tomllib

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def parse_pinned_deps_from_uv_lock(lock: dict) -> list[Requirement]:
    reqs = []

    for package in lock.get("package", []):
        # skip the main package
        if package.get("source", {}).get("virtual") or package.get("source", {}).get(
            "editable"
        ):
            continue

        name = package.get("name")
        version = package.get("version")
        req_string = f"{name}=={version}"

        if markers := package.get("resolution-markers", []):
            req_string += f" ; {' and '.join(markers)}"

        req = Requirement(req_string)
        req.name = canonicalize_name(req.name)
        reqs.append(req)

    return reqs


class PinnedExtraMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "pinned_extra"

    def update(self, metadata: dict):
        with open(f"{self.root}/uv.lock", "rb") as f:
            lock = tomllib.load(f)

        direct_reqs = [
            canonicalize_name(Requirement(req).name)
            for req in metadata.get("dependencies", [])
        ]
        pinned_reqs = parse_pinned_deps_from_uv_lock(lock)

        # add the pinned dependencies to the project table
        metadata["optional-dependencies"] = {
            "pinned": [str(req) for req in pinned_reqs if req.name in direct_reqs]
        }


@hookimpl
def hatch_register_metadata_hook() -> type[PinnedExtraMetadataHook]:
    return PinnedExtraMetadataHook

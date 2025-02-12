import sys
from copy import deepcopy

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from hatch_pinned_extra import PinnedExtraMetadataHook, parse_pinned_deps_from_uv_lock


def test_parse_pinned_deps_from_uv_lock():
    with open("fixtures/project/uv.lock", "rb") as f:
        lock = tomllib.load(f)

    reqs = parse_pinned_deps_from_uv_lock(
        lock,
        dependencies=["annotated-types", "anyio"],
    )
    assert reqs[0].name == "annotated-types"
    assert reqs[0].specifier == "==0.7.0"

    assert reqs[1].name == "anyio"
    assert reqs[1].specifier == "==4.5.2"
    assert str(reqs[1].marker) == 'python_full_version < "3.9"'

    reqs = parse_pinned_deps_from_uv_lock(
        lock,
        dependencies=["anyio"],
    )
    assert reqs[0].name == "anyio"
    assert reqs[0].specifier == "==4.5.2"
    assert str(reqs[0].marker) == 'python_full_version < "3.9"'

    assert reqs[1].name == "anyio"
    assert reqs[1].specifier == "==4.8.0"
    assert str(reqs[1].marker) == (
        'python_full_version >= "3.13" '
        'or (python_full_version >= "3.10" and python_full_version < "3.13") '
        'or python_full_version == "3.9.*"'
    )

    assert reqs[2].name == "exceptiongroup"


def test_update_metadata():
    metadata = {
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
    hook = PinnedExtraMetadataHook("fixtures/project", {"extra-name": "pinned"})

    dst_metadata = deepcopy(metadata)
    hook.update(dst_metadata)

    assert dst_metadata["dependencies"] == metadata["dependencies"]
    assert dst_metadata["optional-dependencies"]["dev"] == metadata["optional-dependencies"]["dev"]

    assert "boto3==1.36.15" in dst_metadata["optional-dependencies"]["pinned"]
    assert (
        'colorama==0.4.6; sys_platform == "win32"'
        in dst_metadata["optional-dependencies"]["pinned"]
    )
    assert (
        'importlib-resources==6.5.2; python_version < "3.10" and python_full_version == "3.9.*"'
        in dst_metadata["optional-dependencies"]["pinned"]
    )


def test_update_metadata_no_optional_deps():
    metadata = {
        "dependencies": [
            "anyio>=4.5.2",
            "boto3>=1.36.15",
            "colorama; sys_platform == 'win32'",
            "exceptiongroup>=1.2.2",
            "importlib-resources; python_version < '3.10'",
            "fastapi>=0.115.8",
        ],
    }
    hook = PinnedExtraMetadataHook("fixtures/project", {"extra-name": "pinned"})

    dst_metadata = deepcopy(metadata)
    hook.update(dst_metadata)

    assert dst_metadata["dependencies"] == metadata["dependencies"]

    assert "boto3==1.36.15" in dst_metadata["optional-dependencies"]["pinned"]
    assert (
        'colorama==0.4.6; sys_platform == "win32"'
        in dst_metadata["optional-dependencies"]["pinned"]
    )
    assert (
        'importlib-resources==6.5.2; python_version < "3.10" and python_full_version == "3.9.*"'
        in dst_metadata["optional-dependencies"]["pinned"]
    )

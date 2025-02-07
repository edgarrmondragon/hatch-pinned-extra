import tomllib

from hatch_pinned_extra import parse_pinned_deps_from_uv_lock


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

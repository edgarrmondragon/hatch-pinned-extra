import tomllib

from hatch_pinned_extra import parse_pinned_deps_from_uv_lock


def test_parse_pinned_deps_from_uv_lock():
    with open("fixtures/project/uv.lock", "rb") as f:
        lock = tomllib.load(f)

    reqs = parse_pinned_deps_from_uv_lock(lock)
    assert reqs[0].name == "annotated-types"
    assert reqs[0].specifier == "==0.7.0"

    assert reqs[1].name == "anyio"
    assert reqs[1].specifier == "==4.5.2"
    assert str(reqs[1].marker) == 'python_full_version < "3.9"'

#!/usr/bin/env -S uv run --script

# /// script
# dependencies = ["nox>=2025.2.9"]
# ///

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

import os
from pathlib import Path

import nox

nox.needs_version = ">=2025.2.9"
nox.options.default_venv_backend = "uv"
nox.options.reuse_venv = "yes"

PYPROJECT = nox.project.load_toml()
python_versions = nox.project.python_versions(PYPROJECT)


def _install_env(session: nox.Session) -> dict[str, str]:
    """Get the environment variables for the install command.

    Args:
        session: The Nox session.

    Returns:
        The environment variables.
    """
    env = {"UV_PROJECT_ENVIRONMENT": session.virtualenv.location}
    if isinstance(session.python, str):
        env["UV_PYTHON"] = session.python

    return env


@nox.session(python=python_versions, tags=["test"])
def tests(session: nox.Session) -> None:
    """Execute pytest tests and compute coverage."""
    session.run_install(
        "uv",
        "sync",
        "--locked",
        "--no-dev",
        "--group=testing",
        env=_install_env(session),
    )

    try:
        session.run("coverage", "run", "--parallel", "-m", "pytest", *session.posargs)
    finally:
        if session.interactive:
            session.notify("coverage", posargs=[])


@nox.session(name="test-lowest", python=python_versions[0], tags=["test"])
def test_lowest_requirements(session: nox.Session) -> None:
    """Test the package with the lowest dependency versions."""
    tmpdir = Path(session.create_tmp())
    tmpfile = tmpdir / "requirements.txt"
    tmpfile.unlink(missing_ok=True)
    session.run_install(
        "uv",
        "pip",
        "compile",
        "pyproject.toml",
        f"--python={session.python}",
        "--universal",
        "--no-sources",
        "--resolution=lowest-direct",
        f"-o={tmpfile.as_posix()}",
    )

    install_env = _install_env(session)
    session.run_install(
        "uv",
        "sync",
        "--locked",
        "--no-dev",
        "--group=testing",
        env=install_env,
    )
    session.install("-r", f"{tmpdir}/requirements.txt", env=install_env, silent=False)
    session.run("pytest", *session.posargs)


@nox.session(tags=["typing"])
def typing(session: nox.Session) -> None:
    """Run type checking with mypy."""
    session.run_install(
        "uv",
        "sync",
        "--locked",
        "--no-dev",
        "--group=typing",
        env=_install_env(session),
    )
    session.run("mypy", "src", "tests")


@nox.session(tags=["typing"])
def ty(session: nox.Session) -> None:
    """Run type checking with ty."""
    session.run_install(
        "uv",
        "sync",
        "--locked",
        "--no-dev",
        "--group=typing",
        env=_install_env(session),
    )
    session.run(
        "ty",
        "check",
        f"--output-format={'github' if os.getenv('GITHUB_ACTIONS') == 'true' else 'concise'}",
        "src",
        "tests",
    )


@nox.session(default=False)
def coverage(session: nox.Session) -> None:
    """Generate coverage report."""
    args = session.posargs or ["report", "-m"]

    session.run_install(
        "uv",
        "sync",
        "--locked",
        "--no-dev",
        "--group=testing",
        env=_install_env(session),
    )

    if not session.posargs and any(Path().glob(".coverage.*")):
        session.run("coverage", "combine")

    session.run("coverage", *args)


@nox.session
@nox.parametrize("fixture", ["extras", "project"])
def lock(session: nox.Session, fixture: str) -> None:
    with session.chdir(f"fixtures/{fixture}"):
        session.run(
            "uv",
            "lock",
            env={
                "UV_EXCLUDE_NEWER": "2026-01-15",
            },
        )


if __name__ == "__main__":
    nox.main()

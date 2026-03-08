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
import warnings
from pathlib import Path
from typing import Any

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl

from hatch_pinned_extra._compat import read_toml
from hatch_pinned_extra._pylock import parse_pinned_deps_from_pylock
from hatch_pinned_extra._uv import parse_pinned_deps_from_uv_lock


def strtobool(val: str) -> bool:
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.

    Case is ignored in string comparisons.

    Re-implemented from distutils.util.strtobool to avoid importing distutils.

    Args:
        val: The string to convert to a boolean.

    Returns:
        True if the string represents a truthy value, False otherwise.

    Raises:
        ValueError: If the string is not a valid representation of a boolean.
    """
    val = val.lower()
    if val in {"y", "yes", "t", "true", "on", "1"}:
        return True
    if val in {"n", "no", "f", "false", "off", "0"}:
        return False

    msg = f"invalid truth value {val!r}"
    raise ValueError(msg)


class PinnedExtraMetadataHook(MetadataHookInterface):
    """Hatch plugin that adds a packaging extra with pinned dependencies from a lock file."""

    PLUGIN_NAME = "pinned_extra"

    def update(self, metadata: dict[str, Any]) -> None:
        # Check if plugin is enabled via environment variable
        if not strtobool(os.getenv("HATCH_PINNED_EXTRA_ENABLE", "no")):
            warnings.warn(
                "HATCH_PINNED_EXTRA_ENABLE is not set, pinned extra is disabled",
                UserWarning,
                stacklevel=1,
            )
            return

        extra_name = self.config.get("extra-name", "pinned")
        lockfile = str(self.config.get("lockfile", "uv.lock"))
        root_path = Path(self.root)

        lock_path = root_path / lockfile
        if not lock_path.exists():
            warnings.warn(
                f"{lock_path} was not found in {self.root}. "
                f"Skipping generation of the '{extra_name}' extra.",
                UserWarning,
                stacklevel=2,
            )
            return

        if lockfile == "uv.lock":
            lock = read_toml(lock_path)
            pinned_reqs = parse_pinned_deps_from_uv_lock(lock, metadata["dependencies"])

        elif lockfile.startswith("pylock.") and lockfile.endswith(".toml"):
            lock = read_toml(lock_path)
            pinned_reqs = parse_pinned_deps_from_pylock(lock, metadata["dependencies"])

        else:
            warnings.warn(
                (
                    f"The configured lockfile '{lockfile}' is neither uv.lock nor a "
                    f"pylock.*.toml file. Skipping generation of the '{extra_name}' extra."
                ),
                UserWarning,
                stacklevel=2,
            )
            return

        # add the pinned dependencies to the project table
        metadata.setdefault("optional-dependencies", {})
        metadata["optional-dependencies"][extra_name] = [str(req) for req in pinned_reqs]


@hookimpl
def hatch_register_metadata_hook() -> type[PinnedExtraMetadataHook]:
    return PinnedExtraMetadataHook  # pragma: no cover

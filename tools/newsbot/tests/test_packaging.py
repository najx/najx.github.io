"""Every module the CLI can reach must import from a clean install.

This exists because it did not. typesafe_sdk, anthropic and trafilatura were
installed by hand in the development venv and absent from pyproject, and the
gap stayed invisible: judge is imported lazily, inside the branch that only
runs when TYPESAFE_API_KEY is set, so the daily job passed for as long as the
key was missing from CI. Adding the key broke the job.
"""

import importlib
import tomllib
from pathlib import Path

import pytest

MODULES = ["cli", "fetch", "judge", "models", "normalize", "render",
           "sources", "store", "verify", "weekly", "write"]


@pytest.mark.parametrize("name", MODULES)
def test_every_module_imports(name):
    importlib.import_module(f"newsbot.{name}")


def test_every_third_party_import_is_declared():
    """A lazy import must still be a declared dependency."""
    root = Path(__file__).resolve().parents[1]
    declared = tomllib.loads((root / "pyproject.toml").read_text())
    names = {d.split(">")[0].split("=")[0].split("[")[0].strip().lower()
             for d in declared["project"]["dependencies"]}
    # distribution name -> module name, where they differ
    aliases = {"pyyaml": "yaml", "typesafe-sdk": "typesafe_sdk"}
    modules = {aliases.get(n, n.replace("-", "_")) for n in names}

    seen = set()
    for path in (root / "newsbot").glob("*.py"):
        for line in path.read_text().splitlines():
            line = line.strip()
            for prefix in ("import ", "from "):
                if line.startswith(prefix):
                    top = line[len(prefix):].split()[0].split(".")[0]
                    if top and not line.startswith(("from .", "import .")):
                        seen.add(top)
    stdlib = {"__future__", "concurrent", "dataclasses", "datetime", "hashlib",
              "html", "json", "logging", "os", "pathlib", "re", "secrets",
              "sys", "typing", "unicodedata", "urllib", "argparse", "newsbot"}
    third_party = seen - stdlib
    missing = third_party - modules
    assert not missing, f"imported but not declared in pyproject: {sorted(missing)}"

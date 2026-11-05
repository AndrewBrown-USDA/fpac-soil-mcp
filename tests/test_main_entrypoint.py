"""The server entrypoint imports the checked-out source, not an installed copy."""

import runpy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def clean_path(monkeypatch):
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != str(ROOT / "src")])


def test_entrypoint_puts_src_first(clean_path):
    namespace = runpy.run_path(str(ROOT / "main.py"), run_name="entrypoint_test")
    assert namespace["SRC_DIR"] == ROOT / "src"
    assert sys.path[0] == str(ROOT / "src")


def test_entrypoint_does_not_duplicate_src(clean_path):
    runpy.run_path(str(ROOT / "main.py"), run_name="entrypoint_test")
    runpy.run_path(str(ROOT / "main.py"), run_name="entrypoint_test")
    assert sys.path.count(str(ROOT / "src")) == 1


def test_package_resolves_to_this_checkout(tmp_path):
    # Fresh interpreter, started outside the repo, so nothing is already imported.
    code = (
        "import runpy, sys; "
        f"runpy.run_path({str(ROOT / 'main.py')!r}, run_name='entrypoint_test'); "
        "import fpac_soil_mcp; print(fpac_soil_mcp.__file__)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    assert Path(result.stdout.strip()).resolve().is_relative_to(ROOT / "src")

from types import SimpleNamespace

from scripts import start_app


def test_prepare_frontend_uses_prebuilt_assets_without_running_npm(monkeypatch, tmp_path):
    monkeypatch.setenv("FPAC_FRONTEND_PREBUILT", "1")

    def unexpected_npm_run(*args, **kwargs):
        raise AssertionError("npm must not run when frontend assets are prebuilt")

    monkeypatch.setattr(start_app.subprocess, "run", unexpected_npm_run)

    assert start_app.prepare_frontend(tmp_path)


def test_prepare_frontend_installs_and_builds_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("FPAC_FRONTEND_PREBUILT", raising=False)
    calls = []

    def npm_run(command, **kwargs):
        calls.append((command, kwargs["cwd"]))
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(start_app.shutil, "which", lambda _: "npm")
    monkeypatch.setattr(start_app.subprocess, "run", npm_run)

    assert start_app.prepare_frontend(tmp_path)
    assert calls == [
        (["npm", "ci"], tmp_path),
        (["npm", "run", "build"], tmp_path),
    ]

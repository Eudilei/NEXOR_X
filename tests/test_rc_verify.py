
import importlib.util
from pathlib import Path


def load_verifier():
    path = (
        Path(__file__).parents[1]
        / "tools"
        / "rc_verify.py"
    )
    spec = importlib.util.spec_from_file_location(
        "rc_verify",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_repo(tmp_path, verifier):
    (tmp_path / "src/nexor_x/api").mkdir(parents=True)
    (tmp_path / "src/nexor_x/operations").mkdir(parents=True)
    (tmp_path / "src/nexor_x/validation").mkdir(parents=True)
    (tmp_path / "docs").mkdir()

    (tmp_path / "pyproject.toml").write_text(
        '[project]\\nversion = "0.57.0"\\n',
        encoding="utf-8",
    )
    (tmp_path / "src/nexor_x/__init__.py").write_text(
        '__version__ = "0.57.0"\\n',
        encoding="utf-8",
    )
    (tmp_path / "src/nexor_x/api/app.py").write_text(
        "\\n".join(verifier.REQUIRED_ENDPOINT_MARKERS),
        encoding="utf-8",
    )

    for rel in verifier.REQUIRED_FILES:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(
                "live_allowed = False\\n",
                encoding="utf-8",
            )

    return tmp_path


def test_clean_repo_passes(tmp_path):
    verifier = load_verifier()
    repo = make_repo(tmp_path, verifier)
    report = verifier.verify(repo)
    assert report["status"] == "RC_VERIFY_PASS"
    assert report["live_allowed"] is False


def test_missing_file_fails(tmp_path):
    verifier = load_verifier()
    repo = make_repo(tmp_path, verifier)
    (repo / verifier.REQUIRED_FILES[0]).unlink()
    report = verifier.verify(repo)
    assert report["status"] == "RC_VERIFY_FAIL"
    assert "critical_files_present" in report["failed_checks"]


def test_live_true_marker_fails(tmp_path):
    verifier = load_verifier()
    repo = make_repo(tmp_path, verifier)
    target = repo / "src/nexor_x/validation/final_completion.py"
    target.write_text(
        'live_allowed = True\\n',
        encoding="utf-8",
    )
    report = verifier.verify(repo)
    assert "no_live_true_in_rc_gates" in report["failed_checks"]


def test_forbidden_cache_fails(tmp_path):
    verifier = load_verifier()
    repo = make_repo(tmp_path, verifier)
    cache = repo / "src/nexor_x/__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_bytes(b"x")
    report = verifier.verify(repo)
    assert "no_forbidden_artifacts" in report["failed_checks"]

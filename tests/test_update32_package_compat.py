from pathlib import Path


def test_update_does_not_replace_legacy_evidence_initializer() -> None:
    # This test runs after payload application in GitHub, where the repository
    # initializer must still contain its legacy exports and the new collector.
    text = Path("src/nexor_x/evidence/__init__.py").read_text(encoding="utf-8")
    assert "EvidenceEngine" in text
    assert "EvidenceDirection" in text
    assert "EvidenceCollector" in text

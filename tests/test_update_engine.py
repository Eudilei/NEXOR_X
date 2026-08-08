from nexor_x.update_engine import Version, VersionError


def test_semver_parse_and_order() -> None:
    assert Version.parse("0.23.0") > Version.parse("0.22.0")
    assert str(Version.parse("v1.2.3")) == "1.2.3"


def test_invalid_version_rejected() -> None:
    try:
        Version.parse("23")
    except VersionError:
        pass
    else:
        raise AssertionError("Invalid version should fail")


def test_next_version_rules() -> None:
    assert Version.parse("0.23.0").is_next_after(Version.parse("0.22.0"))
    assert Version.parse("0.22.1").is_next_after(Version.parse("0.22.0"))
    assert not Version.parse("0.24.0").is_next_after(Version.parse("0.22.0"))

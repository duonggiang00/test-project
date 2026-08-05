import pytest

from scripts.test_database import validate_test_database_target


BASE_URL = "postgresql://app:password@localhost:5432/app"


def test_accepts_a_separate_local_test_database():
    target = validate_test_database_target(
        BASE_URL,
        "postgresql://app:password@localhost:5432/app_test",
    )

    assert target.target.database == "app_test"
    assert target.target.host == "localhost"


def test_accepts_equivalent_localhost_aliases():
    target = validate_test_database_target(
        BASE_URL,
        "postgresql://app:password@127.0.0.1:5432/app_test",
    )

    assert target.target.host == "127.0.0.1"


@pytest.mark.parametrize(
    "target_url, expected_message",
    [
        (BASE_URL, "must differ"),
        ("postgresql://app:password@localhost:5432/app_ci", "must end with _test"),
        ("postgresql://app:password@db.example.test:5432/app_test", "only manages local"),
        ("sqlite:///app_test", "must use PostgreSQL"),
        ("postgresql://app:password@localhost:5432/postgres", "admin database"),
    ],
)
def test_rejects_unsafe_database_targets(target_url, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        validate_test_database_target(BASE_URL, target_url)

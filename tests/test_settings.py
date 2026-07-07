from pathlib import Path

import yaml

from app.settings import Settings


def test_git_publication_defaults_to_disabled_without_repository_inspection(
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "not-a-repository"

    settings = Settings(
        _env_file=None,
        knowledge_base_path=missing_root,
    )

    assert settings.git_publication_enabled is False
    assert settings.knowledge_base_path == missing_root
    assert not missing_root.exists()


def test_git_publication_enabled_parses_environment_value(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GIT_PUBLICATION_ENABLED", "true")

    settings = Settings(_env_file=None)

    assert settings.git_publication_enabled is True


def test_openai_configuration_is_optional_and_blank_allowed(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_MODEL", "")

    settings = Settings(_env_file=None)

    assert settings.openai_api_key == ""
    assert settings.openai_model == ""


def test_compose_forwards_git_publication_setting_to_app_and_worker() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())

    for service_name in ("app", "worker"):
        assert compose["services"][service_name]["environment"][
            "GIT_PUBLICATION_ENABLED"
        ] == "${GIT_PUBLICATION_ENABLED:-false}"


def test_compose_forwards_openai_configuration_to_app_only() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())

    assert compose["services"]["app"]["environment"]["OPENAI_API_KEY"] == (
        "${OPENAI_API_KEY:-}"
    )
    assert compose["services"]["app"]["environment"]["OPENAI_MODEL"] == (
        "${OPENAI_MODEL:-}"
    )
    assert "OPENAI_API_KEY" not in compose["services"]["worker"]["environment"]
    assert "OPENAI_MODEL" not in compose["services"]["worker"]["environment"]

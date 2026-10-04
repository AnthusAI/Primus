from __future__ import annotations

from unittest.mock import patch

import pytest

from primus.config.loader import ConfigLoader, ConfigSource
from proxy.config import Settings
from proxy.store import PostgresStore
from proxy.store_factory import create_store
from proxy.virtuus_store import VirtuusStore


PROXY_ENV_VARS = (
    "PRIMUS_STORE",
    "PRIMUS_BACKEND_MODE",
    "PRIMUS_DATA_DIR",
    "PRIMUS_VIRTUUS_DATA_DIR",
    "PRIMUS_PROXY_UPSTREAM_DISABLED",
    "PRIMUS_PROXY_AUTH_MODE",
    "PRIMUS_PROXY_DATABASE_URL",
)


@pytest.fixture
def clean_proxy_env(monkeypatch):
    for name in PROXY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_yaml_config_selects_virtuus_store_without_preset_env(clean_proxy_env, tmp_path):
    config_file = tmp_path / ".primus" / "config.yaml"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        """
primus:
  store: virtuus
  backend_mode: local
  data_dir: .primus/data
  proxy:
    auth_mode: trusted_open
    upstream_disabled: true
""".strip()
        + "\n"
    )

    loader = ConfigLoader()
    with patch.object(loader, "config_sources", [ConfigSource(config_file, 1, True)]):
        loader.load_config()

    settings = Settings.from_env()
    store = create_store(settings)

    assert settings.store_type == "virtuus"
    assert settings.backend_mode == "local"
    assert settings.virtuus_data_dir == ".primus/data"
    assert settings.auth_mode == "trusted_open"
    assert settings.upstream_disabled is True
    assert isinstance(store, VirtuusStore)
    assert store.data_dir == ".primus/data"


def test_env_vars_override_yaml_virtuus_settings(clean_proxy_env, tmp_path, monkeypatch):
    config_file = tmp_path / ".primus" / "config.yaml"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        """
primus:
  store: virtuus
  data_dir: .primus/data
""".strip()
        + "\n"
    )

    loader = ConfigLoader()
    with patch.object(loader, "config_sources", [ConfigSource(config_file, 1, True)]):
        loader.load_config()

    monkeypatch.setenv("PRIMUS_STORE", "postgres")

    settings = Settings.from_env()
    store = create_store(settings)

    assert settings.store_type == "postgres"
    assert isinstance(store, PostgresStore)


def test_postgres_default_when_yaml_absent(clean_proxy_env):
    loader = ConfigLoader()
    with patch.object(loader, "config_sources", []):
        loader.load_config()

    settings = Settings.from_env()
    store = create_store(settings)

    assert settings.store_type == "postgres"
    assert isinstance(store, PostgresStore)

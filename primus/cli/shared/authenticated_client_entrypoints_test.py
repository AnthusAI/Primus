import importlib
from types import SimpleNamespace

import pytest

from primus.cli.shared import client_utils


@pytest.mark.parametrize(
    "module_name",
    [
        "primus.cli.evaluation.evaluations",
        "primus.cli.scorecard.scorecards",
        "primus.cli.score.scores",
        "primus.cli.dataset.datasets",
    ],
)
def test_resource_cli_client_factories_use_centralized_application_auth(
    monkeypatch,
    module_name,
):
    module = importlib.import_module(module_name)
    authenticated_client = SimpleNamespace(api_url="https://sandbox.example/graphql")

    monkeypatch.setattr(
        client_utils,
        "create_client",
        lambda: authenticated_client,
    )
    monkeypatch.setattr(
        module,
        "PrimusDashboardClient",
        lambda *args, **kwargs: pytest.fail(
            "resource CLI must not construct the legacy API-key client directly"
        ),
    )

    assert module.create_client() is authenticated_client

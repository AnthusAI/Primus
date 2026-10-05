import pytest
import pandas as pd
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from primus.cli.prediction.predictions import predict_score_with_individual_loading


@pytest.mark.asyncio
async def test_predict_score_with_individual_loading_uses_item_when_text_missing():
    sample_row = pd.DataFrame([{"item_id": "item-123", "text": ""}])
    fake_item = SimpleNamespace(id="item-123", text="from item")
    fake_result = SimpleNamespace(parameters=SimpleNamespace(key="TestScore", name="TestScore"), value=True)
    fake_scorecard = SimpleNamespace(
        score_entire_text=AsyncMock(return_value={"TestScore": fake_result}),
        get_accumulated_costs=lambda: {"total_cost": 0},
    )

    with patch("primus.cli.shared.client_utils.create_client", return_value=Mock()):
        with patch("primus.cli.shared.direct_memoized_resolvers.direct_memoized_resolve_scorecard_identifier", return_value="scid"):
            with patch("primus.cli.shared.fetch_scorecard_structure.fetch_scorecard_structure", return_value={"id": "scid"}):
                with patch("primus.cli.shared.identify_target_scores.identify_target_scores", return_value=[{"name": "TestScore"}]):
                    with patch("primus.cli.shared.iterative_config_fetching.iteratively_fetch_configurations", return_value={"TestScore": {"name": "TestScore"}}):
                        with patch("primus.cli.prediction.predictions.Scorecard.create_instance_from_api_data", return_value=fake_scorecard):
                            with patch("primus.dashboard.api.models.item.Item.get_by_id", return_value=fake_item):
                                await predict_score_with_individual_loading(
                                    "scid",
                                    "TestScore",
                                    sample_row,
                                    used_item_id="item-123",
                                    no_cache=True,
                                    yaml_only=True,
                                    specific_version=None,
                                )

    call_kwargs = fake_scorecard.score_entire_text.call_args.kwargs
    assert call_kwargs["item"] is fake_item

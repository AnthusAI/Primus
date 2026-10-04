import sys
import os
import asyncio
from primus.cli.shared.client_utils import create_client
from primus.cli.report.utils import resolve_account_id_for_command
from primus.dashboard.api.models.score import Score
from primus.dashboard.api.models.scorecard import Scorecard

client = create_client()
account_id = resolve_account_id_for_command(client, None)

async def run():
    query = """
    query ListScorecards {
        listScorecards(limit: 1000) {
            items {
                id
                name
                externalId
            }
        }
    }
    """
    res = client.execute(query)
    for item in res.get('listScorecards', {}).get('items', []):
        if item:
            print(f"{item.get('name')} (ID: {item.get('externalId')})")

asyncio.run(run())


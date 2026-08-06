# Usage Examples

## Python

```python
import asyncio

from forecast_ai.config_store import ConfigStore
from forecast_ai.pipelines.forecast import ForecastPipeline


async def main():
    config = ConfigStore().load_config()
    pipeline = ForecastPipeline(config)

    result = await pipeline.run_forecast(
        question="Will the selected event happen before expiry?",
        market_id="MARKET_ID_OR_SLUG",
        venue="polymarket",
    )

    print(result.probability)
    print(result.confidence.score)
    for prediction in result.individual_predictions:
        print(prediction.agent_name, prediction.summary)


asyncio.run(main())
```

## Browse API

```bash
curl "http://localhost:30000/markets/browse?venue=kalshi&category=Economy"
```

## Prediction API

```bash
curl -X POST "http://localhost:30000/predict" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_SERVER_API_KEY" \
  -d '{"question":"Will this market resolve Yes?","market_id":"MARKET_ID","venue":"kalshi"}'
```

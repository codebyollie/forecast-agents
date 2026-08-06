"""Minimal self-hosted Forecast AI example."""

import asyncio

from forecast_ai.config_store import ConfigStore
from forecast_ai.pipelines.forecast import ForecastPipeline


async def main() -> None:
    config = ConfigStore().load_config()
    pipeline = ForecastPipeline(config)

    result = await pipeline.run_forecast(
        question="Will the selected event resolve Yes?",
        market_id="custom_market",
    )

    print(f"Consensus probability: {result.probability:.1%}")
    print(f"Confidence: {result.confidence.score:.1%}")
    for prediction in result.individual_predictions:
        print(f"\n[{prediction.agent_name}] {prediction.probability:.1%}")
        print(prediction.summary or prediction.reasoning)


if __name__ == "__main__":
    asyncio.run(main())

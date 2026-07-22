# Usage Examples

## Running in Python

```python
import asyncio
from forecast_ai.config import ForecastConfig
from forecast_ai.pipelines.forecast import ForecastPipeline

async def main():
    cfg = ForecastConfig()
    pipeline = ForecastPipeline(cfg)
    
    result = await pipeline.run_forecast(
        "Will Bitcoin hit $200k in 2026?", 
        market_id="btc_200k"
    )
    print(f"Consensus Prob: {result.probability * 100}%")

asyncio.run(main())
```

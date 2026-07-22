"""
Forecast AI programmatically run prediction pipeline demo.
"""

import asyncio
from forecast_ai.config import ForecastConfig
from forecast_ai.pipelines.forecast import ForecastPipeline

async def main():
    # Instantiate config with API credentials
    config = ForecastConfig()
    
    # Optional: Configure provider details
    # config.providers["openai"].api_key = "your-api-key"
    
    # Initialize the Pipeline
    pipeline = ForecastPipeline(config)
    
    question = "Will Ethereum gas fee average stay below 20 Gwei in Q3?"
    print(f"Running Forecast AI Pipeline on: '{question}'...\n")
    
    # Run the collaborative multi-agent forecast
    result = await pipeline.run_forecast(question, market_id="eth_gas_below_20_gwei")
    
    print("=" * 40)
    print(f"Consensus Probability: {result.probability * 100:.1f}%")
    print(f"Consensus Confidence:  {result.confidence.score * 100:.1f}%")
    print("=" * 40)
    print("\nReasoning Summary:")
    print(result.metadata.get("summary_reasoning"))

if __name__ == "__main__":
    asyncio.run(main())

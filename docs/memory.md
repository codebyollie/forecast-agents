# Memory Layer

The Memory Layer logs forecasts and tracks performance over time:
- Logs forecasts to `forecasts.json`.
- Evaluates outcome correctness and modifies agent weights via Bayesian calibration.
- Stores reputations in `reputation.json`.

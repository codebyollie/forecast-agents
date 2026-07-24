# 🔬 FactsAI Deep Research Integration

[FactsAI](https://factsai.org/docs) is a serverless, pay-per-request Deep Research API built on Cloudflare's edge by the [Polyfactual](https://www.polyfactual.com/) team (recipients of a Polymarket Grant). It provides synthesized research answers along with verifiable citations (`url`, `title`, `author`, `publishedDate`) from across the web.

---

## 📌 Overview

In Forecast AI, FactsAI acts as a supplementary, high-confidence evidence source for specialized agents:
- **`ResearchAgent`**: Folds synthesized academic and web research answers plus top citations into its evidence context.
- **`MacroAgent`**: Folds macro-economic and central bank research synthesis with cited primary sources into its reasoning.

> [!NOTE]
> FactsAI is **disabled by default (`FACTSAI_ENABLED=false`)** to prevent unexpected API costs for self-hosting users. It can be enabled on-demand via configuration or environment variables.

---

## ⚙️ Setup & Self-Hosting Guide

To enable FactsAI Deep Research on your Forecast AI backend instance:

1. **Get an API Key**:
   - Visit [factsai.org](https://factsai.org/) and sign in with your email.
   - Generate your personal API key (format: `forecast_...` or similar token).

2. **Configure Environment Variables**:
   Set the following environment variables on your server (Render, Railway, Docker, or `.env` file):

   ```bash
   FACTSAI_API_KEY="your_factsai_api_key_here"
   FACTSAI_ENABLED="true"
   ```

3. **API Endpoint & Parameters**:
   - **Endpoint**: `POST https://deep-research-api.degodmode3-33.workers.dev/answer`
   - **Auth Header**: `Authorization: Bearer {FACTSAI_API_KEY}`
   - **Payload**: `{"query": "<market_question>"}` (automatically truncated to max 1,000 characters).

---

## 💰 Pricing & Cost Projections

FactsAI operates on a transparent pay-as-you-go model at **$0.012 per request**.

### Cost Estimation Example (Public Feed - 6 Curated Topics):
- **Refresh Cadence**: 2 long-horizon topics (every 6h = 8 runs/day) + 4 short-horizon topics (every 2h = 48 runs/day) = **56 scheduled updates/day**.
- **Every Cycle Execution**: 56 runs/day × 2 agents (Research + Macro) = 112 API requests/day = **~$40.32/month**.
- **Coarse Cadence (`coarse_refresh_interval_cycles: 2`)**: Executing FactsAI once every 2 refresh cycles cuts cost to **~$20.16/month**, well within the backend's `$50.00/month` public feed spend-guard limit (`SERVER_PUBLIC_FEED_MONTHLY_BUDGET_USD`).

---

## 🛡️ Error Handling & Graceful Fallback

Forecast AI handles FactsAI API responses strictly:
- **401 Unauthorized**: Invalid or missing API key.
- **402 Payment Required**: Insufficient FactsAI credits.
- **429 Too Many Requests**: Exceeded 100 requests/minute rate limit.
- **500+ Server Error**: Temporary Cloudflare Worker or upstream error.

> [!IMPORTANT]
> **Graceful Fallback**: If FactsAI returns any HTTP error code or if the network request fails, the backend logs a warning (`[Research] FactsAI call failed. Falling back to standard evidence.`) and proceeds with standard reasoning. **FactsAI failure will never crash a forecast or stop agent execution.**

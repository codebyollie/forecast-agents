# 🔑 Configuring API Keys & LLM Providers

Forecast AI supports multi-provider LLM forecasting with automatic fallback chains (e.g., primary OpenAI with Gemini fallback). You can configure your credentials using either interactive CLI prompts or environment variables.

---

## 1. Local Installations (`forecast setup`)

For local machines or virtual machines where you run Forecast AI directly:

1. Run the interactive configuration wizard:
   ```bash
   forecast setup
   ```
2. Select your default LLM provider (e.g. `openai`) and enter your API key when prompted.
3. **Adding a Secondary/Fallback Provider**: You can re-run `forecast setup` at any time to configure additional providers (e.g., set up `openai` first, then run `forecast setup` again for `gemini`). Existing configuration keys for other providers will be preserved.
4. Your settings are stored in `~/.forecast_ai/config.yaml`.

---

## 2. Hosted Deployments (Render, Railway, GitHub Codespaces)

On hosted cloud platforms without an interactive terminal, Forecast AI automatically reads secrets from **environment variables** (taking precedence over `config.yaml`):

| Environment Variable | Description | Example |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | OpenAI API Secret Key | `sk-proj-...` |
| `GEMINI_API_KEY` | Google Gemini API Key | `AIzaSy...` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key | `sk-ant-...` |
| `OPENROUTER_API_KEY` | OpenRouter API Key | `sk-or-v1-...` |
| `KALSHI_API_KEY` | Kalshi API Key (optional) | `your_kalshi_key` |
| `SUPABASE_URL` | Supabase Project URL | `https://xyz.supabase.co` |
| `SUPABASE_KEY` | Supabase Anon / Service Role Key | `eyJhbGci...` |
| `PRIVY_APP_ID` | Privy Backend App ID | `cmrymien...` |
| `PRIVY_APP_SECRET` | Privy Backend App Secret | `privy_app_secret_...` |
| `FACTSAI_API_KEY` | FactsAI Deep Research API Key | `forecast_b0db...` |
| `FACTSAI_ENABLED` | Enable FactsAI (`true`/`false`) | `true` |
| `SERVER_PORT` | FastAPI Server Port | `30000` |

### Setting Environment Variables on Cloud Platforms:
- **Render**: Navigate to your Service Settings → Environment Variables (or fill in the `sync: false` prompts during Blueprint deployment).
- **Railway**: Go to your Service Variables tab and enter key-value pairs matching `.env.example`.
- **GitHub Codespaces**: Set Repository Secrets or create a `.env` file in the root directory.

---

## 🛡️ Security & Architecture Note

> [!IMPORTANT]
> **Privy Frontend vs. Backend Credential Distinction**:
> - **Backend Host (`forecast-agents`)**: Set `PRIVY_APP_ID` AND `PRIVY_APP_SECRET` for server-side JWT verification of user profiles (`GET /profile/me`).
> - **Frontend Website (`forecast-website`)**: Set `NEXT_PUBLIC_PRIVY_APP_ID` ONLY. **NEVER expose `PRIVY_APP_SECRET` on the frontend!**

"""
Base Forecast Agent implementation.

Defines the core prompt generation and output parsing logic for specialized agents.
"""

from abc import ABC, abstractmethod
import json
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlsplit, urlunsplit
from ..models.evidence import Evidence
from ..models.prediction import Prediction
from ..models.confidence import ConfidenceScore
from ..providers.base import BaseProvider
from ..config import ForecastConfig

class ForecastAgent(ABC):
    def __init__(
        self,
        name: str,
        provider: BaseProvider,
        config: ForecastConfig,
        provider_manager: Optional[Any] = None,
        primary_provider_name: str = "openai"
    ):
        self.name = name
        self.provider = provider
        self.config = config
        self.provider_manager = provider_manager
        self.primary_provider_name = primary_provider_name

    @abstractmethod
    def get_system_instruction(self) -> str:
        """
        Define the specialized system prompt for this agent.
        """
        pass

    async def forecast(
        self,
        question: str,
        evidence: List[Evidence],
        model_override: Optional[str] = None,
    ) -> Prediction:
        """
        Run the agent prediction flow using LLM.
        """
        import os
        from datetime import datetime, timezone
        
        now_utc = datetime.now(timezone.utc)
        today_date_str = now_utc.strftime("%B %d, %Y")
        current_year = now_utc.year

        raw_system_instruction = self.get_system_instruction()
        system_instruction = (
            f"{raw_system_instruction}\n\n"
            f"CRITICAL TEMPORAL CONTEXT:\n"
            f"- Today's current real-world date is: {today_date_str} (Year {current_year}).\n"
            f"- All market resolution questions, target dates, and historical timelines MUST be evaluated relative to {current_year}.\n"
            f"- Do NOT assume past years (such as 2024 or 2025) are the current year."
        )

        # Clone evidence list so we can append agent-specific evidence safely
        active_evidence = list(evidence or [])
        prediction_citations: List[Dict[str, str]] = []
        citation_keys = set()
        research_providers = set()
        provider_insights: Dict[str, str] = {}
        provider_statuses: Dict[str, str] = {}

        def infer_provider(item: Evidence) -> str:
            metadata_provider = str((item.metadata or {}).get("provider") or "").strip()
            if metadata_provider:
                return metadata_provider
            source_name = item.source_name.lower()
            if "facts" in source_name:
                return "FactsAI"
            if "tavily" in source_name:
                return "Tavily"
            if "reddit" in source_name:
                return "Reddit"
            if "twitter" in source_name or source_name == "x":
                return "X"
            if "polymarket" in source_name:
                return "Polymarket"
            if "kalshi" in source_name:
                return "Kalshi"
            if "web search" in source_name or "web citation" in source_name:
                return "OpenAI Web Search"
            if "news" in source_name or "rss" in source_name:
                return "News/RSS"
            if "blockchain" in source_name or "onchain" in source_name:
                return "On-chain"
            return item.source_name.strip() or "Source"

        def citation_key(url: str, title: str) -> str:
            if url:
                try:
                    parsed = urlsplit(url.strip())
                    host = parsed.netloc.lower().removeprefix("www.")
                    path = parsed.path.rstrip("/") or "/"
                    return urlunsplit((parsed.scheme.lower() or "https", host, path, "", ""))
                except Exception:
                    return url.strip().lower()
            return re.sub(r"\s+", " ", title.strip().lower())

        def add_citation(
            title: str,
            url: str,
            provider: str,
            source_type: str = "web",
        ) -> None:
            clean_title = (title or "Source").strip()
            clean_url = (url or "").strip()
            if not clean_url:
                return
            key = citation_key(clean_url, clean_title)
            if not key or key in citation_keys:
                return
            citation_keys.add(key)
            clean_provider = (provider or "Source").strip()
            research_providers.add(clean_provider)
            prediction_citations.append({
                "title": clean_title,
                "url": clean_url,
                "provider": clean_provider,
                "sourceType": source_type or "web",
            })

        # Web research block
        # Priority:  1. FactsAI  (Research / Macro / News)
        #            2. OpenAI Web Search  (fallback for above + primary for Social / Reddit)
        facts_key = (
            getattr(self.config.facts_ai, "api_key", "")
            or os.getenv("FACTS_AI_API_KEY", "")
            or os.getenv("FACTSAI_API_KEY", "")
        )
        openai_key = (
            getattr(self.config.providers.get("openai", object()), "api_key", "")
            or os.getenv("OPENAI_API_KEY", "")
        )
        facts_ai_error = None
        agent_name = self.name.lower()
        facts_ai_enabled = (
            getattr(self.config.facts_ai, "enabled", False)
            or os.getenv("FACTSAI_ENABLED", "").lower() in ("true", "1", "yes")
        )

        for item in active_evidence:
            source_type = str((item.metadata or {}).get("source_type") or "web")
            if item.url and source_type != "summary":
                add_citation(
                    item.title or item.source_name,
                    item.url,
                    infer_provider(item),
                    source_type,
                )

        # 1. FactsAI for Research / Macro / News
        facts_used = False
        if agent_name in ("research", "macro", "news") and facts_ai_enabled and facts_key:
            provider_statuses["FactsAI"] = "requested"
            try:
                from ..sources.facts_ai import FactsAISource
                facts_source = FactsAISource(
                    api_key=facts_key,
                    api_url=self.config.facts_ai.api_url,
                    query_max_length=self.config.facts_ai.query_max_length,
                )
                facts_query = {
                    "news": f"Latest verified reporting and official statements relevant to: {question}",
                    "research": f"Primary documents, official reports, and expert research relevant to: {question}",
                    "macro": f"Macroeconomic, regulatory, and systemic drivers relevant to: {question}",
                }[agent_name]
                res = await facts_source.fetch_deep_research(facts_query)
                import logging as _logging
                _logging.getLogger(__name__).info(
                    f"[{self.name}] FactsAI OK. Answer: {len(res.get('answer',''))} chars, "
                    f"Citations: {len(res.get('citations', []))}"
                )
                if res.get("answer"):
                    facts_answer = str(res["answer"]).strip()
                    provider_insights["FactsAI"] = facts_answer[:1500]
                    active_evidence.append(Evidence(
                        source_name="FactsAI Deep Research",
                        content=res["answer"],
                        relevance_score=0.95,
                        title=f"FactsAI Synthesis: {question[:60]}",
                        url="https://factsai.org",
                        metadata={"provider": "FactsAI", "source_type": "summary"},
                    ))
                for c in res.get("citations", []):
                    title = c.get("title") or "Cited Source"
                    url   = c.get("url") or ""
                    if url or title:
                        add_citation(title, url, "FactsAI", "research")
                        active_evidence.append(Evidence(
                            source_name="FactsAI Citation",
                            content=f"FactsAI Verified Source: {title}",
                            relevance_score=0.90,
                            title=title,
                            url=url,
                            metadata={"provider": "FactsAI", "source_type": "research"},
                        ))
                facts_used = bool(res.get("answer") or res.get("citations"))
                if facts_used:
                    research_providers.add("FactsAI")
                    provider_statuses["FactsAI"] = "active"
                else:
                    provider_statuses["FactsAI"] = "empty"
            except Exception as e:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    f"[{self.name}] FactsAI failed ({e}). Falling back to OpenAI Web Search."
                )
                facts_ai_error = f"FactsAI unavailable: {e}"
                provider_statuses["FactsAI"] = "unavailable"

        # Social and Reddit agents must use platform-native results. Tavily is
        # preferred because it supports domain filters and returns source URLs.
        tavily_key = (
            getattr(self.config.tavily, "api_key", "")
            or os.getenv("TAVILY_API_KEY", "")
        )
        tavily_enabled = (
            getattr(self.config.tavily, "enabled", False)
            or os.getenv("TAVILY_ENABLED", "").lower() in ("true", "1", "yes")
        )
        specialized_domains = {
            "social": ["x.com", "twitter.com", "bsky.app", "threads.net"],
            "reddit": ["reddit.com"],
        }
        if agent_name in specialized_domains and tavily_enabled and tavily_key:
            try:
                from ..sources.tavily_search import TavilySearchSource
                tavily_source = TavilySearchSource(api_key=tavily_key, enabled=True)
                platform_label = "social media" if agent_name == "social" else "Reddit"
                tavily_evidence = await tavily_source.fetch(
                    f"Current {platform_label} discussions and sentiment about: {question}",
                    limit=5,
                    include_domains=specialized_domains[agent_name],
                )
                for item in tavily_evidence:
                    tavily_source_type = str(item.metadata.get("source_type") or "web")
                    item.metadata["provider"] = "Tavily"
                    item.metadata["source_type"] = tavily_source_type if tavily_source_type == "summary" else agent_name
                    active_evidence.append(item)
                    if tavily_source_type == "summary" and item.content:
                        provider_insights["Tavily"] = str(item.content).strip()[:1200]
                    if item.url:
                        add_citation(item.title or platform_label, item.url, "Tavily", agent_name)
                if tavily_evidence:
                    research_providers.add("Tavily")
            except Exception as e:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    f"[{self.name}] Tavily platform search failed: {e}"
                )

        # 2. OpenAI Web Search
        # Runs as FALLBACK for Research/Macro/News (when FactsAI failed)
        # Runs as PRIMARY for Social (Twitter/X) and Reddit agents
        web_search_query = None
        if agent_name in ("research", "macro", "news") and not facts_used:
            web_search_query = question
        elif agent_name == "social" and not any(c.get("sourceType") == "social" for c in prediction_citations):
            web_search_query = (
                f'site:x.com OR site:twitter.com OR site:bsky.app social sentiment about: "{question[:300]}"'
            )
        elif agent_name == "reddit" and not any(c.get("sourceType") == "reddit" for c in prediction_citations):
            web_search_query = (
                f'site:reddit.com Reddit community discussion arguments about: "{question[:300]}"'
            )

        if web_search_query and openai_key:
            try:
                from ..sources.web_search import WebSearchSource
                ws = WebSearchSource(api_key=openai_key)
                ws_res = await ws.search(web_search_query)
                import logging as _logging
                _logging.getLogger(__name__).info(
                    f"[{self.name}] Web Search OK. Answer: {len(ws_res.get('answer',''))} chars, "
                    f"Citations: {len(ws_res.get('citations', []))}"
                )
                source_label = (
                    "Web Search (FactsAI fallback)" if agent_name in ("research", "macro", "news")
                    else f"Web Search ({agent_name.capitalize()})"
                )
                if agent_name in ("research", "macro", "news"):
                    provider_statuses["OpenAI Web Search"] = "fallback"
                allowed_domains = specialized_domains.get(agent_name)
                accepted_citations = []
                for c in ws_res.get("citations", []):
                    url = (c.get("url") or "").strip()
                    if allowed_domains and url:
                        host = urlsplit(url).netloc.lower().removeprefix("www.")
                        if not any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains):
                            continue
                    accepted_citations.append(c)

                if ws_res.get("answer") and (accepted_citations or not allowed_domains):
                    active_evidence.append(Evidence(
                        source_name=source_label,
                        content=ws_res["answer"],
                        relevance_score=0.92,
                        title=f"Web Research: {question[:60]}",
                        url="https://openai.com",
                        metadata={"provider": "OpenAI Web Search", "source_type": "summary"},
                    ))
                for c in accepted_citations:
                    title = c.get("title") or "Web Source"
                    url   = c.get("url") or ""
                    if url or title:
                        add_citation(title, url, "OpenAI Web Search", agent_name if allowed_domains else "web")
                        active_evidence.append(Evidence(
                            source_name="Web Citation",
                            content=f"Cited: {title}",
                            relevance_score=0.87,
                            title=title,
                            url=url,
                            metadata={
                                "provider": "OpenAI Web Search",
                                "source_type": agent_name if allowed_domains else "web",
                            },
                        ))
            except Exception as e:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    f"[{self.name}] Web Search also failed: {e}."
                )
                if not facts_ai_error:
                    facts_ai_error = f"Web search failed: {e}"

        # Format evidence context
        evidence_context = f"CURRENT DATE: {today_date_str}\n"
        if active_evidence:
            evidence_context += "AVAILABLE EVIDENCE:\n"
            for i, ev in enumerate(active_evidence):
                evidence_context += f"[{i+1}] Source: {ev.source_name} | Date: {ev.timestamp} | Relevance: {ev.relevance_score:.2f}\n"
                if ev.title:
                    evidence_context += f"Title: {ev.title}\n"
                evidence_context += f"Content: {ev.content}\n"
                if ev.url:
                    evidence_context += f"Link: {ev.url}\n"
                evidence_context += "-" * 40 + "\n"
        else:
            evidence_context += "NO DIRECT EXTERNAL EVIDENCE AVAILABLE FOR THIS ANALYSIS.\n"

        user_prompt = f"""
MARKET QUESTION: "{question}"
CURRENT YEAR: {current_year} (Today is {today_date_str})

{evidence_context}

Please analyze the available evidence relative to the question above.
You must output a JSON object containing:
- "probability": A float between 0.0 and 1.0 representing your estimated likelihood of the event resolving to YES.
- "confidence": A float between 0.0 and 1.0 representing your certainty of this forecast.
- "summary": One plain-language sentence stating your conclusion and the most important reason.
- "key_drivers": Up to 3 short evidence-backed factors supporting your forecast.
- "counter_signals": Up to 2 short factors pointing toward the opposite outcome.
- "uncertainties": Up to 2 concrete data gaps, conflicts, or resolution risks.
- "watch_next": Up to 2 specific developments that could materially change the probability.
- "reasoning": A concise 2-3 sentence technical rationale. Do not repeat the bullet fields verbatim.
- "warnings": A list of warning messages regarding data sparseness, conflicts, or high volatility.

Return ONLY valid JSON. Do not include markdown wraps or additional conversation.
"""

        temperature = 0.3
        if self.name in self.config.agents:
            temperature = self.config.agents[self.name].temperature

        gen_kwargs = {
            "system_prompt": system_instruction,
            "user_prompt": user_prompt,
            "temperature": temperature
        }
        if model_override is not None:
            gen_kwargs["model_override"] = model_override

        if self.provider_manager:
            raw_response = await self.provider_manager.generate_with_fallback(
                primary_name=self.primary_provider_name,
                agent_name=self.name,
                **gen_kwargs
            )
        else:
            raw_response = await self.provider.generate(**gen_kwargs)

        # Parse JSON output
        probability = 0.5
        confidence_val = 0.5
        reasoning = "Failed to parse agent reasoning."
        summary = ""
        key_drivers: List[str] = []
        counter_signals: List[str] = []
        uncertainties: List[str] = []
        watch_next: List[str] = []
        warnings = []
        if facts_ai_error:
            warnings.append(facts_ai_error)

        try:
            # Clean markdown code block wraps if present
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)
            
            data = json.loads(cleaned.strip())
            probability = float(data.get("probability", 0.5))
            confidence_val = float(data.get("confidence", 0.5))
            reasoning = str(data.get("reasoning", ""))
            summary = str(data.get("summary", "")).strip()

            def clean_list(key: str, limit: int) -> List[str]:
                value = data.get(key, [])
                if not isinstance(value, list):
                    return []
                return [str(item).strip() for item in value if str(item).strip()][:limit]

            key_drivers = clean_list("key_drivers", 3)
            counter_signals = clean_list("counter_signals", 2)
            uncertainties = clean_list("uncertainties", 2)
            watch_next = clean_list("watch_next", 2)
            warnings.extend(list(data.get("warnings", [])))
        except Exception:
            # Fallback regex parsing if JSON fails
            prob_match = re.search(r'"probability"\s*:\s*(0\.\d+|1\.0|0|1)', raw_response)
            if prob_match:
                try:
                    probability = float(prob_match.group(1))
                except Exception:
                    pass
            
            conf_match = re.search(r'"confidence"\s*:\s*(0\.\d+|1\.0|0|1)', raw_response)
            if conf_match:
                try:
                    confidence_val = float(conf_match.group(1))
                except Exception:
                    pass

            reason_match = (
                re.search(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_response, re.DOTALL) or
                re.search(r'"reasoning"\s*:\s*"(.*?)"\s*,\s*"(?:warnings|confidence|probability)', raw_response, re.DOTALL)
            )
            if reason_match:
                raw_reason = reason_match.group(1)
                reasoning = (
                    raw_reason.replace(r'\"', '"')
                              .replace(r'\\', '\\')
                              .replace(r'\n', '\n')
                              .replace(r'\t', '\t')
                )
            else:
                reasoning = f"Raw output: {raw_response[:500]}..."

        if not summary:
            summary = re.split(r"(?<=[.!?])\s+", reasoning.strip(), maxsplit=1)[0] if reasoning.strip() else "No concise summary was returned."

        confidence = ConfidenceScore(score=confidence_val, warnings=warnings)
        
        return Prediction(
            agent_name=self.name,
            probability=probability,
            confidence=confidence,
            reasoning=reasoning,
            summary=summary,
            key_drivers=key_drivers,
            counter_signals=counter_signals,
            uncertainties=uncertainties,
            watch_next=watch_next,
            evidence_used=active_evidence,
            citations=prediction_citations[:8],
            research_providers=sorted(research_providers),
            provider_insights=provider_insights,
            provider_statuses=provider_statuses,
        )

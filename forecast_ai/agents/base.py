"""
Base Forecast Agent implementation.

Defines the core prompt generation and output parsing logic for specialized agents.
"""

from abc import ABC, abstractmethod
import json
import re
from typing import List, Dict, Any, Optional
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

    async def forecast(self, question: str, evidence: List[Evidence], is_public_feed: bool = False, model_override: Optional[str] = None) -> Prediction:
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

        # ── Web Research block ──────────────────────────────────────────────
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

        # ── 1. FactsAI for Research / Macro / News ─────────────────────────
        facts_used = False
        if agent_name in ("research", "macro", "news") and facts_key:
            try:
                from ..sources.facts_ai import FactsAISource
                facts_source = FactsAISource(
                    api_key=facts_key,
                    api_url=self.config.facts_ai.api_url,
                    query_max_length=self.config.facts_ai.query_max_length,
                )
                res = await facts_source.fetch_deep_research(question)
                import logging as _logging
                _logging.getLogger(__name__).info(
                    f"[{self.name}] FactsAI OK. Answer: {len(res.get('answer',''))} chars, "
                    f"Citations: {len(res.get('citations', []))}"
                )
                if res.get("answer"):
                    active_evidence.append(Evidence(
                        source_name="FactsAI Deep Research",
                        content=res["answer"],
                        relevance_score=0.95,
                        title=f"FactsAI Synthesis: {question[:60]}",
                        url="https://factsai.org",
                    ))
                for c in res.get("citations", []):
                    title = c.get("title") or "Cited Source"
                    url   = c.get("url") or ""
                    if url or title:
                        prediction_citations.append({"title": title, "url": url})
                        active_evidence.append(Evidence(
                            source_name="FactsAI Citation",
                            content=f"FactsAI Verified Source: {title}",
                            relevance_score=0.90,
                            title=title,
                            url=url,
                        ))
                facts_used = True
            except Exception as e:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    f"[{self.name}] FactsAI failed ({e}). Falling back to OpenAI Web Search."
                )
                facts_ai_error = f"FactsAI unavailable: {e}"

        # ── 2. OpenAI Web Search ────────────────────────────────────────────
        # Runs as FALLBACK for Research/Macro/News (when FactsAI failed)
        # Runs as PRIMARY for Social (Twitter/X) and Reddit agents
        web_search_query = None
        if agent_name in ("research", "macro", "news") and not facts_used:
            web_search_query = question
        elif agent_name == "social":
            web_search_query = (
                f'Twitter X social media discussion sentiment about: "{question[:300]}"'
            )
        elif agent_name == "reddit":
            web_search_query = (
                f'Reddit community discussion arguments about: "{question[:300]}"'
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
                if ws_res.get("answer"):
                    active_evidence.append(Evidence(
                        source_name=source_label,
                        content=ws_res["answer"],
                        relevance_score=0.92,
                        title=f"Web Research: {question[:60]}",
                        url="https://openai.com",
                    ))
                for c in ws_res.get("citations", []):
                    title = c.get("title") or "Web Source"
                    url   = c.get("url") or ""
                    if url or title:
                        prediction_citations.append({"title": title, "url": url})
                        active_evidence.append(Evidence(
                            source_name="Web Citation",
                            content=f"Cited: {title}",
                            relevance_score=0.87,
                            title=title,
                            url=url,
                        ))
                # Clear FactsAI error since we recovered via web search
                facts_ai_error = None
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
- "reasoning": A detailed explanation of your analysis, highlighting supporting evidence and potential caveats.
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
                is_public_feed=is_public_feed,
                **gen_kwargs
            )
        else:
            raw_response = await self.provider.generate(**gen_kwargs)

        # Parse JSON output
        probability = 0.5
        confidence_val = 0.5
        reasoning = "Failed to parse agent reasoning."
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

        confidence = ConfidenceScore(score=confidence_val, warnings=warnings)
        
        return Prediction(
            agent_name=self.name,
            probability=probability,
            confidence=confidence,
            reasoning=reasoning,
            evidence_used=active_evidence,
            citations=prediction_citations
        )

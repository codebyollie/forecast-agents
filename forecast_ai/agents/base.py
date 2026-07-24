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

    async def forecast(self, question: str, evidence: List[Evidence], is_public_feed: bool = False) -> Prediction:
        """
        Run the agent prediction flow using LLM.
        """
        system_instruction = self.get_system_instruction()
        
        # Clone evidence list so we can append agent-specific evidence safely
        active_evidence = list(evidence or [])
        prediction_citations: List[Dict[str, str]] = []

        # Wire FactsAI for Research and Macro Agents if enabled
        if self.name.lower() in ("research", "macro") and self.config.facts_ai.enabled and self.config.facts_ai.api_key:
            try:
                from ..sources.facts_ai import FactsAISource
                facts_source = FactsAISource(
                    api_key=self.config.facts_ai.api_key,
                    api_url=self.config.facts_ai.api_url,
                    query_max_length=self.config.facts_ai.query_max_length
                )
                res = await facts_source.fetch_deep_research(question)
                
                if res.get("answer"):
                    active_evidence.append(Evidence(
                        source_name="FactsAI Deep Research",
                        content=res["answer"],
                        relevance_score=0.95,
                        title=f"FactsAI Synthesis for: {question[:60]}",
                        url="https://factsai.org"
                    ))
                
                for c in res.get("citations", []):
                    title = c.get("title") or "Cited Source"
                    url = c.get("url") or ""
                    if url or title:
                        prediction_citations.append({"title": title, "url": url})
                        active_evidence.append(Evidence(
                            source_name="FactsAI Citation",
                            content=f"FactsAI Verified Source: {title}",
                            relevance_score=0.90,
                            title=title,
                            url=url
                        ))
            except Exception as e:
                # Fall back gracefully to standard reasoning without failing the whole forecast
                import logging
                logging.getLogger(__name__).warning(
                    f"[{self.name}] FactsAI call failed: {e}. Falling back to standard evidence."
                )

        # Format evidence context
        evidence_context = ""
        if active_evidence:
            evidence_context = "AVAILABLE EVIDENCE:\n"
            for i, ev in enumerate(active_evidence):
                evidence_context += f"[{i+1}] Source: {ev.source_name} | Date: {ev.timestamp} | Relevance: {ev.relevance_score:.2f}\n"
                if ev.title:
                    evidence_context += f"Title: {ev.title}\n"
                evidence_context += f"Content: {ev.content}\n"
                if ev.url:
                    evidence_context += f"Link: {ev.url}\n"
                evidence_context += "-" * 40 + "\n"
        else:
            evidence_context = "NO DIRECT EXTERNAL EVIDENCE AVAILABLE FOR THIS ANALYSIS.\n"

        user_prompt = f"""
MARKET QUESTION: "{question}"

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

        if self.provider_manager:
            raw_response = await self.provider_manager.generate_with_fallback(
                primary_name=self.primary_provider_name,
                system_prompt=system_instruction,
                user_prompt=user_prompt,
                temperature=temperature,
                agent_name=self.name,
                is_public_feed=is_public_feed
            )
        else:
            raw_response = await self.provider.generate(
                system_prompt=system_instruction,
                user_prompt=user_prompt,
                temperature=temperature
            )

        # Parse JSON output
        probability = 0.5
        confidence_val = 0.5
        reasoning = "Failed to parse agent reasoning."
        warnings = []

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
            warnings = list(data.get("warnings", []))
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

            reason_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', raw_response)
            if reason_match:
                reasoning = reason_match.group(1)
            else:
                reasoning = f"Raw output: {raw_response[:200]}..."

        confidence = ConfidenceScore(score=confidence_val, warnings=warnings)
        
        return Prediction(
            agent_name=self.name,
            probability=probability,
            confidence=confidence,
            reasoning=reasoning,
            evidence_used=active_evidence,
            citations=prediction_citations
        )

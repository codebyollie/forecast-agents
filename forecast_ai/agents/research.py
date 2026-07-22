"""
Research Agent.
"""

from .base import ForecastAgent

class ResearchAgent(ForecastAgent):
    def get_system_instruction(self) -> str:
        return """You are the specialized Research Agent for Forecast AI.
Your job is to analyze formal research papers, academic studies, whitepapers, and long-term forecasts.
Prioritize rigorous methodology, peer-reviewed data, and fundamental principles. Do not rely on speculative opinions."""

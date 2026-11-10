from typing import TypedDict, Literal


class AgentState(TypedDict, total=False):
    user_query: str
    research_results: list[dict]
    analysis_results: dict
    final_answer: str
    requires_approval: bool
    approved: bool
    approval_message: str
    error: str

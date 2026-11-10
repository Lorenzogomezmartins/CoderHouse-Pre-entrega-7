
from langgraph.graph import StateGraph, START, END

from app.state import AgentState
from app.agents.research_agent import research_agent
from app.agents.analyst_agent import analyst_agent
from app.hitl import approval_node, is_critical_query


def prepare_task(state: AgentState) -> dict:
    query = state.get("user_query", "")

    return {
        "requires_approval": is_critical_query(query),
        "approved": False,
    }


def route_after_approval(state: AgentState) -> str:
    if state.get("requires_approval") and not state.get("approved"):
        return "finalize"

    return "research"


def finalize_task(state: AgentState) -> dict:
    if state.get("requires_approval") and not state.get("approved"):
        return {
            "final_answer": (
                "La tarea no fue aprobada. "
                "No se ejecutó el análisis."
            )
        }

    documents = state.get("research_results", [])
    analysis_results = state.get("analysis_results", {})
    analysis = analysis_results.get("llm_analysis", "")

    if not analysis:
        analysis = "No se obtuvo un análisis del agente."

    if documents:
        titles = "\n".join(
            f"- {document.get('title', 'Documento sin título')}"
            for document in documents
        )
        source_text = (
            f"Documentos encontrados:\n{titles}"
        )
    else:
        source_text = (
            "No se encontraron documentos en la base de conocimiento. "
            "El análisis se realizó con conocimiento general."
        )

    answer = (
        f"{source_text}\n\n"
        f"Análisis:\n{analysis}"
    )

    return {"final_answer": answer}


def build_graph(checkpointer=None):
    builder = StateGraph(AgentState)

    builder.add_node("prepare", prepare_task)
    builder.add_node("approval", approval_node)
    builder.add_node("research", research_agent)
    builder.add_node("analyst", analyst_agent)
    builder.add_node("finalize", finalize_task)

    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "approval")

    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "research": "research",
            "finalize": "finalize",
        },
    )

    builder.add_edge("research", "analyst")
    builder.add_edge("analyst", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)

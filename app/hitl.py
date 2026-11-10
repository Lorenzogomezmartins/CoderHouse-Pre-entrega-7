
import unicodedata
from langgraph.types import interrupt


CRITICAL_KEYWORDS = {
    "elimin",       # eliminar, eliminación, eliminando
    "borr",         # borrar, borrado
    "public",       # publicar, publicación
    "envi",         # enviar, envío
    "compr",        # comprar, compra
    "pag",          # pagar, pago
    "transfer",     # transferir, transferencia
    "produccion",
    "modificar datos",
    "ejecutar comando",
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(
        character
        for character in text
        if unicodedata.category(character) != "Mn"
    )


def is_critical_query(query: str) -> bool:
    normalized_query = normalize_text(query)
    return any(
        keyword in normalized_query
        for keyword in CRITICAL_KEYWORDS
    )


def approval_node(state: dict) -> dict:
    if not state.get("requires_approval", False):
        return {"approved": True}

    decision = interrupt({
        "type": "human_approval",
        "message": "Esta tarea requiere aprobación humana.",
        "query": state.get("user_query", ""),
    })

    approved = (
        decision.get("approved", False)
        if isinstance(decision, dict)
        else bool(decision)
    )

    return {
        "approved": approved,
        "approval_message": (
            "Tarea aprobada por un usuario."
            if approved
            else "Tarea rechazada por un usuario."
        ),
    }

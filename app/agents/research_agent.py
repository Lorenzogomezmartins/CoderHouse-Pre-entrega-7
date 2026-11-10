import json
import re
from pathlib import Path

STOP_WORDS = {
    "de", "la", "el", "los", "las", "un", "una", "y", "o",
    "en", "por", "para", "con", "que", "del", "al", "es",
    "se", "su", "sus", "como", "sobre", "entre", "más"
}


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    return {word for word in words if word not in STOP_WORDS}


def search_knowledge_base(query: str, limit: int = 5) -> list[dict]:
    file_path = Path(__file__).resolve().parents[2] / "data" / "knowledge_base.json"

    with file_path.open("r", encoding="utf-8-sig") as file:
        documents = json.load(file)

    query_words = tokenize(query)
    results = []

    for document in documents:
        content = f"{document['title']} {document['content']}"
        document_words = tokenize(content)
        matches = query_words.intersection(document_words)

        if matches:
            results.append({
                **document,
                "relevance": len(matches),
                "matched_terms": sorted(matches)
            })

    results.sort(key=lambda item: item["relevance"], reverse=True)
    return results[:limit]


def research_agent(state: dict) -> dict:
    query = state["user_query"]
    results = search_knowledge_base(query)

    return {
        "research_results": results
    }

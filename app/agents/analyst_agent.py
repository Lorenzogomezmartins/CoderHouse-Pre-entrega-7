
import os
import time
import threading

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

gemini_semaphore = threading.Semaphore(1)


def extract_text(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)

    return str(content)


def analyst_agent(state: dict) -> dict:
    research_results = state.get("research_results", [])

    metrics = {
        "documents_analyzed": len(research_results),
        "matched_terms": sum(
            len(item.get("matched_terms", []))
            for item in research_results
        ),
    }

    prompt = f"""
Analizá los resultados de investigación y respondé en español.
Si no hay documentos suficientes, aclaralo y respondé con conocimiento
general, identificando esa limitación.

Consulta: {state.get("user_query", "")}
Resultados: {research_results}
Métricas: {metrics}
"""

    analysis = None
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }
    last_error = None

    try:
        model = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            timeout=60,
            max_retries=0,
        )

        for attempt in range(3):
            try:
                with gemini_semaphore:
                    response = model.invoke(prompt)

                analysis = extract_text(response.content)
                usage = response.usage_metadata or usage
                break

            except Exception as error:
                last_error = error
                message = str(error).upper()

                temporary_error = any(
                    code in message
                    for code in (
                        "503",
                        "504",
                        "UNAVAILABLE",
                        "DEADLINE_EXCEEDED",
                        "RESOURCE_EXHAUSTED",
                        "429",
                    )
                )

                if not temporary_error or attempt == 2:
                    break

                wait_seconds = 5 * (2 ** attempt)
                print(
                    f"Gemini temporalmente no disponible. "
                    f"Intento {attempt + 1}/3. "
                    f"Nuevo intento en {wait_seconds}s."
                )
                time.sleep(wait_seconds)

        if analysis is None:
            analysis = (
                "Gemini no pudo completar el análisis después de "
                f"3 intentos. Último error: {str(last_error)[:300]}"
            )
            print(f"ERROR GEMINI: {last_error}")

    except Exception as error:
        analysis = f"No se pudo inicializar Gemini: {str(error)[:300]}"
        print(f"ERROR GEMINI: {error}")

    return {
        "analysis_results": {
            "metrics": metrics,
            "llm_analysis": analysis,
            "token_usage": usage,
        }
    }

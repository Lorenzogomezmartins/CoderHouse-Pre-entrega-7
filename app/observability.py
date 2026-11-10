import os
from dotenv import load_dotenv


def configure_observability():
    load_dotenv(override=False)

    api_key = os.getenv("LANGSMITH_API_KEY")
    tracing = "true" if api_key else "false"

    os.environ["LANGSMITH_TRACING"] = tracing
    os.environ["LANGCHAIN_TRACING_V2"] = tracing
    os.environ["LANGSMITH_PROJECT"] = os.getenv(
        "LANGSMITH_PROJECT",
        "pre-entrega-7",
    )

    if api_key:
        print(
            "LangSmith habilitado. Proyecto:",
            os.environ["LANGSMITH_PROJECT"],
        )
    else:
        print(
            "AVISO: falta LANGSMITH_API_KEY. "
            "Las trazas no se enviarán a LangSmith."
        )

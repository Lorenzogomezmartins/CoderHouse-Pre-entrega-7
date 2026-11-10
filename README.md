# Pre-entrega 7 — API de producción y monitoreo activo

API REST desarrollada con **FastAPI** que permite ejecutar un sistema multiagente basado en **LangGraph**, utilizando Gemini como modelo de lenguaje, Redis para persistencia y LangSmith para observabilidad.

El sistema permite enviar tareas de forma asíncrona, consultar su estado, conservar el estado de ejecución y solicitar aprobación humana para operaciones críticas.

## Tecnologías utilizadas

- **Python**
- **FastAPI:** API REST y ejecución asíncrona de solicitudes.
- **LangGraph:** coordinación del flujo multiagente.
- **Gemini (Google):** modelo de lenguaje.
- **Redis:** almacenamiento de tareas, estados y persistencia.
- **LangSmith:** trazabilidad y monitoreo de ejecuciones.
- **Uvicorn:** servidor ASGI.
- **Pydantic:** validación de datos.

## Arquitectura del proyecto

```text
pre-entrega-7/
│
├── app/
│   ├── agents/
│   │   ├── analyst_agent.py
│   │   └── research_agent.py
│   │
│   ├── graph.py
│   ├── hitl.py
│   ├── main.py
│   ├── observability.py
│   ├── redis_checkpointer.py
│   ├── state.py
│   └── worker.py
│
├── data/
│   └── knowledge_base.json
│
├── screenshots/
│
├── scripts/
│   └── test_concurrent.py
│
├── tests/
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── requirements.txt
```

### Flujo de ejecución

1. El cliente envía una tarea mediante la API.
2. La API genera un identificador único y devuelve una respuesta HTTP 202.
3. El worker procesa la tarea en segundo plano.
4. LangGraph coordina los agentes de investigación y análisis.
5. Redis conserva el estado de las tareas y los checkpoints.
6. LangSmith registra las trazas de ejecución.
7. Si la tarea es crítica, el flujo solicita aprobación humana antes de continuar.

## Requisitos previos

- Python 3.11 o superior.
- Redis en ejecución.
- Una API Key de Google AI Studio para Gemini.
- Una API Key de LangSmith para observabilidad.

## Instalación y configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/Lorenzogomezmartins/CoderHouse-Pre-entrega-7.git
cd CoderHouse-Pre-entrega-7
```

### 2. Crear y activar el entorno virtual

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar las variables de entorno

Crear un archivo `.env` en la raíz del proyecto tomando como referencia `.env.example`.

```env
REDIS_URL=redis://localhost:6379/0

GOOGLE_API_KEY=TU_API_KEY_DE_GEMINI
GEMINI_MODEL=gemini-3.5-flash-lite

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=TU_API_KEY_DE_LANGSMITH
LANGSMITH_PROJECT=pre-entrega-7
```

**Importante:** las claves de API son privadas. No deben publicarse en GitHub.

### 5. Iniciar Redis

El proyecto utiliza Redis para almacenar los estados de las tareas y la persistencia del grafo.

Verificar que Redis esté disponible en:

```text
redis://localhost:6379/0
```

### 6. Ejecutar la API

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

La API estará disponible en:

```text
http://127.0.0.1:8000
```

Documentación interactiva:

```text
http://127.0.0.1:8000/docs
```

## Endpoints disponibles

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/health` | Verificación del estado de la API. |
| POST | `/tasks` | Crear y enviar una tarea para procesamiento asíncrono. |
| GET | `/tasks/{job_id}` | Consultar el estado y resultado de una tarea. |
| POST | `/tasks/{job_id}/approve` | Enviar la decisión de aprobación humana. |

Los esquemas de solicitud y respuesta se encuentran disponibles en la documentación Swagger de `/docs`.

## Sistema multiagente

El flujo está implementado mediante LangGraph y utiliza los siguientes componentes:

- **Research Agent:** recupera información relevante de la base de conocimiento local.
- **Analyst Agent:** procesa la información recuperada y genera un análisis utilizando Gemini.
- **Approval Node:** gestiona las solicitudes de aprobación humana para tareas críticas.
- **Finalize Node:** construye la respuesta final del procesamiento.

## Human-in-the-Loop (HITL)

El sistema identifica determinadas operaciones críticas, como eliminar, borrar, publicar, enviar, comprar o transferir.

Cuando una tarea requiere aprobación, el flujo utiliza interrupciones de LangGraph para detener la ejecución y esperar una decisión humana.

La decisión se envía mediante el endpoint de aprobación, permitiendo continuar o rechazar el procesamiento.

## Persistencia y observabilidad

### Redis

Redis se utiliza para:

- Guardar el estado de cada tarea.
- Consultar los resultados mediante su identificador.
- Persistir los checkpoints del flujo de LangGraph.
- Mantener la información necesaria para reanudar ejecuciones.

### LangSmith

LangSmith permite monitorear las ejecuciones del sistema, consultar trazas, analizar tiempos de ejecución y observar el uso del modelo.

Proyecto de seguimiento: `pre-entrega-7`.

[Acceder a LangSmith](https://smith.langchain.com/)

## Prueba de concurrencia

El proyecto incluye un script para enviar cinco tareas concurrentes y consultar sus estados:

```bash
python scripts/test_concurrent.py
```

La prueba realizada permitió ejecutar cinco solicitudes simultáneas relacionadas con:

- APIs REST.
- Python.
- MongoDB.
- Inteligencia artificial.
- SQL.

Las cinco tareas finalizaron con estado `COMPLETED` y devolvieron sus respectivos resultados.

## Evidencias

Las capturas de ejecución, monitoreo y pruebas se almacenan en la carpeta `screenshots/`.

## Autor

**Lorenzo Gómez Martins**

Proyecto desarrollado como parte de la formación de **IA Engineering — Coderhouse**.

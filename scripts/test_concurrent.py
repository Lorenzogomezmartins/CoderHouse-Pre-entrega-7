import asyncio
import httpx

BASE_URL = "http://127.0.0.1:8000"

QUERIES = [
    "Explicar qué es una API REST.",
    "Explicar qué es Python y para qué se utiliza.",
    "Describir las ventajas de MongoDB.",
    "Explicar qué es inteligencia artificial.",
    "Describir qué es una base de datos SQL."
]

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        responses = await asyncio.gather(*[
            client.post(
                f"{BASE_URL}/tasks",
                json={"query": query}
            )
            for query in QUERIES
        ])

        jobs = []

        for response in responses:
            print("POST:", response.status_code, response.text)
            if response.status_code == 202:
                jobs.append(response.json()["job_id"])

        print(f"\nTareas creadas: {len(jobs)}")

        for attempt in range(36):
            await asyncio.sleep(5)

            results = await asyncio.gather(*[
                client.get(f"{BASE_URL}/tasks/{job_id}")
                for job_id in jobs
            ])

            states = []
            for response in results:
                data = response.json()
                states.append(data["status"])
                print(data["job_id"], data["status"],
                      data.get("error") or "")

            if all(s in ("COMPLETED", "FAILED", "WAITING_APPROVAL")
                   for s in states):
                break

        print("\nRESULTADO FINAL:")
        for job_id in jobs:
            response = await client.get(f"{BASE_URL}/tasks/{job_id}")
            print(response.json())

asyncio.run(main())

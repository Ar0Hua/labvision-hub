from fastapi import FastAPI

app = FastAPI(title="LabVision Search & Insight Agent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

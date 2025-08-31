from fastapi import FastAPI

app = FastAPI(title="ZeroMerma API")  # OpenAPI docs auto-generated at /docs

@app.get("/holamundo")
def holamundo():
    return {"status": "ok"}

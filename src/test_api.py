# src/test_api.py
from fastapi import FastAPI
import uvicorn
import os

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/test")
async def test_endpoint(request_body: dict):
    return {
        "status": "success",
        "received": request_body
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on port {port}")
    uvicorn.run("src.test_api:app", host="0.0.0.0", port=port)
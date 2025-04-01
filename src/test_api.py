from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import random

app = FastAPI()

class ApiResponse(BaseModel):
    message: str
    status: int
    response_time: float

@app.get("/test/success")
async def test_success():
    """Endpoint that always returns success with varying response times"""
    time.sleep(random.uniform(0.1, 0.5))  # Simulate varying response times
    return ApiResponse(
        message="Success",
        status=200,
        response_time=random.uniform(100, 500)
    )

@app.get("/test/error")
async def test_error():
    """Endpoint that randomly returns errors"""
    if random.random() < 0.3:  # 30% chance of error
        raise HTTPException(status_code=500, detail="Random server error")
    return ApiResponse(
        message="Success",
        status=200,
        response_time=random.uniform(100, 500)
    )

@app.get("/test/slow")
async def test_slow():
    """Endpoint that occasionally has slow response times"""
    if random.random() < 0.2:  # 20% chance of slow response
        time.sleep(random.uniform(1, 3))
    return ApiResponse(
        message="Success",
        status=200,
        response_time=random.uniform(100, 2000)
    )

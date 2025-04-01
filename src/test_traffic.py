import asyncio
import aiohttp
import random
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEST_ENDPOINTS = [
    "http://localhost:8001/test/success",
    "http://localhost:8001/test/error",
    "http://localhost:8001/test/slow"
]

MONITORING_API = "http://localhost:8000/api/v1/logs"

async def send_request(session, url):
    try:
        start_time = datetime.utcnow()
        async with session.get(url) as response:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            status = response.status
            
            # Send log to monitoring system
            log_data = {
                "timestamp": start_time.isoformat(),
                "endpoint": url,
                "response_time": response_time,
                "status_code": status,
                "error": None if status < 400 else await response.text()
            }
            
            try:
                async with session.post(MONITORING_API, json=[log_data]) as mon_response:
                    if mon_response.status != 200:
                        logger.error(f"Failed to send log to monitoring system: {await mon_response.text()}")
            except Exception as e:
                logger.error(f"Error sending log to monitoring system: {str(e)}")
                
            logger.info(f"Request to {url} completed with status {status} in {response_time:.2f}ms")
            
    except Exception as e:
        logger.error(f"Error making request to {url}: {str(e)}")

async def generate_traffic():
    async with aiohttp.ClientSession() as session:
        while True:
            # Generate between 1-5 concurrent requests
            tasks = []
            for _ in range(random.randint(1, 5)):
                url = random.choice(TEST_ENDPOINTS)
                tasks.append(asyncio.create_task(send_request(session, url)))
            
            await asyncio.gather(*tasks)
            # Wait between 1-3 seconds before next batch
            await asyncio.sleep(random.uniform(1, 3))

if __name__ == "__main__":
    try:
        asyncio.run(generate_traffic())
    except KeyboardInterrupt:
        logger.info("Traffic generation stopped by user")

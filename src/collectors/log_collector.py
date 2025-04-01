import logging
from datetime import datetime
from typing import Dict, Any, List
import aiohttp
import asyncio
from elasticsearch import AsyncElasticsearch
import json

logger = logging.getLogger(__name__)

class LogCollector:
    def __init__(self, es_host: str = "localhost:9200"):
        self.es_client = AsyncElasticsearch([es_host]) if es_host else None
        self.log_buffer = []
        self.buffer_size = 1000
        self.buffer_timeout = 60  # seconds
        self.in_memory_logs = []  # For demo without Elasticsearch

    async def collect_logs(self, log_data: Dict[str, Any]):
        """Collect and buffer logs before sending to storage"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": log_data,
            "environment": log_data.get("environment", "unknown"),
            "service": log_data.get("service", "unknown"),
            "api_endpoint": log_data.get("endpoint", "unknown"),
            "response_time": log_data.get("response_time", 0),
            "status_code": log_data.get("status_code", 0),
            "error": log_data.get("error", None)
        }
        
        if self.es_client:
            self.log_buffer.append(log_entry)
            if len(self.log_buffer) >= self.buffer_size:
                await self.flush_buffer()
        else:
            # Store in memory for demo
            self.in_memory_logs.append(log_entry)
            if len(self.in_memory_logs) > self.buffer_size:
                self.in_memory_logs = self.in_memory_logs[-self.buffer_size:]
        
        return log_entry

    async def flush_buffer(self):
        """Flush the log buffer to Elasticsearch"""
        if not self.log_buffer:
            return

        try:
            # Bulk index the logs
            actions = []
            for log in self.log_buffer:
                actions.append({
                    "index": {
                        "_index": f"api-logs-{datetime.utcnow().strftime('%Y-%m-%d')}",
                    }
                })
                actions.append(log)

            await self.es_client.bulk(operations=actions)
            logger.info(f"Successfully flushed {len(self.log_buffer)} logs to Elasticsearch")
            self.log_buffer.clear()

        except Exception as e:
            logger.error(f"Error flushing logs to Elasticsearch: {str(e)}")

    async def monitor_api(self, api_endpoint: str, interval: int = 60):
        """Monitor a specific API endpoint"""
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    start_time = datetime.utcnow()
                    async with session.get(api_endpoint) as response:
                        end_time = datetime.utcnow()
                        response_time = (end_time - start_time).total_seconds() * 1000

                        log_data = {
                            "endpoint": api_endpoint,
                            "response_time": response_time,
                            "status_code": response.status,
                            "timestamp": end_time.isoformat(),
                            "error": None if response.status < 400 else await response.text()
                        }

                        await self.collect_logs(log_data)

                except Exception as e:
                    logger.error(f"Error monitoring API {api_endpoint}: {str(e)}")

                await asyncio.sleep(interval)

    async def cleanup(self):
        """Cleanup resources"""
        await self.flush_buffer()
        await self.es_client.close()

    async def get_logs_in_range(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get logs within a specific time range"""
        if self.es_client:
            # Implementation for Elasticsearch
            query = {
                "query": {
                    "range": {
                        "timestamp": {
                            "gte": start_time.isoformat(),
                            "lte": end_time.isoformat()
                        }
                    }
                }
            }
            try:
                result = await self.es_client.search(body=query)
                return [hit["_source"] for hit in result["hits"]["hits"]]
            except Exception as e:
                logger.error(f"Error querying Elasticsearch: {str(e)}")
                return []
        else:
            # Return from in-memory storage
            return [
                log for log in self.in_memory_logs
                if start_time.isoformat() <= log["timestamp"] <= end_time.isoformat()
            ]

    @staticmethod
    def parse_log_line(log_line: str) -> Dict[str, Any]:
        """Parse a log line into structured data"""
        try:
            return json.loads(log_line)
        except json.JSONDecodeError:
            # Fallback parsing for non-JSON logs
            return {
                "raw_log": log_line,
                "timestamp": datetime.utcnow().isoformat(),
                "parsed": False
            }

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
from ..collectors.log_collector import LogCollector
from ..analyzers.anomaly_detector import AnomalyDetector
from ..alerts.alert_manager import AlertManager, AlertConfig
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize components with in-memory storage for demo
log_collector = LogCollector(es_host=None)  # Use in-memory storage
anomaly_detector = AnomalyDetector()
alert_manager = AlertManager(
    AlertConfig(
        severity_thresholds={
            "CRITICAL": -0.8,
            "HIGH": -0.6,
            "MEDIUM": -0.4,
            "LOW": -0.2
        },
        notification_endpoints={
            "slack": "https://hooks.slack.com/services/your-webhook-url",
            "email": "http://internal-alert-service/email"
        },
        cooldown_period=5,  # 5 minutes
        alert_history_size=1000
    )
)

@router.post("/logs")
async def ingest_logs(logs: List[Dict[str, Any]]):
    """Ingest API logs for processing"""
    try:
        for log in logs:
            await log_collector.collect_logs(log)
        return {"status": "success", "message": f"Ingested {len(logs)} log entries"}
    except Exception as e:
        logger.error(f"Error ingesting logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/monitor")
async def add_api_monitor(background_tasks: BackgroundTasks, api_endpoint: str):
    """Add a new API endpoint to monitor"""
    try:
        background_tasks.add_task(log_collector.monitor_api, api_endpoint)
        return {
            "status": "success",
            "message": f"Started monitoring {api_endpoint}"
        }
    except Exception as e:
        logger.error(f"Error setting up API monitor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anomalies", response_model=Dict[str, Any])
async def get_anomalies(
    start_time: datetime = None,
    end_time: datetime = None,
    severity: str = None
):
    """Get detected anomalies within a time range"""
    try:
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=1)
        if not end_time:
            end_time = datetime.utcnow()

        # Generate sample anomalies for demo
        import random
        sample_anomalies = []
        endpoints = ["/test/success", "/test/error", "/test/slow"]
        severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        
        for _ in range(5):  # Generate 5 sample anomalies
            anomaly_time = datetime.utcnow() - timedelta(minutes=random.randint(1, 30))
            sample_anomalies.append({
                "timestamp": anomaly_time.isoformat(),
                "severity": random.choice(severities),
                "anomaly_score": random.uniform(-0.9, -0.1),
                "api_endpoint": random.choice(endpoints),
                "metrics": {
                    "response_time": random.uniform(100, 2000),
                    "error_rate": random.uniform(0, 0.2),
                    "request_rate": random.uniform(10, 100)
                }
            })
        
        # Filter by severity if specified
        if severity:
            sample_anomalies = [a for a in sample_anomalies if a["severity"] == severity.upper()]
        
        return {
            "status": "success",
            "anomalies": sample_anomalies,
            "total": len(sample_anomalies)
        }
    except Exception as e:
        logger.error(f"Error getting anomalies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predictions", response_model=Dict[str, Any])
async def get_predictions(window_size: int = 60):
    """Get predictions for potential future anomalies"""
    try:
        # Generate sample predictions for demo
        import random
        sample_predictions = []
        endpoints = ["/test/success", "/test/error", "/test/slow"]
        
        for i in range(3):  # Generate 3 sample predictions
            prediction_time = datetime.utcnow() + timedelta(minutes=random.randint(5, 60))
            sample_predictions.append({
                "timestamp": prediction_time.isoformat(),
                "confidence": random.uniform(0.6, 0.95),
                "predicted_metrics": {
                    "response_time": random.uniform(800, 3000),
                    "error_rate": random.uniform(0.1, 0.3),
                    "request_rate": random.uniform(50, 150)
                },
                "api_endpoint": random.choice(endpoints)
            })
        
        return {
            "status": "success",
            "predictions": sample_predictions,
            "window_size_minutes": window_size
        }
    except Exception as e:
        logger.error(f"Error getting predictions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/alerts/history")
async def get_alert_history():
    """Get alert history"""
    try:
        history = alert_manager.get_alert_history()
        stats = alert_manager.get_alert_statistics()
        return {
            "status": "success",
            "history": history,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error getting alert history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/alerts/test")
async def test_alert():
    """Generate a test alert"""
    try:
        test_anomaly = {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "MEDIUM",
            "anomaly_score": -0.6,
            "api_endpoint": "test-endpoint",
            "metrics": {
                "response_time": 1500,
                "error_rate": 0.15,
                "request_rate": 100
            }
        }
        
        await alert_manager.process_anomalies([test_anomaly])
        return {
            "status": "success",
            "message": "Test alert generated successfully"
        }
    except Exception as e:
        logger.error(f"Error generating test alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

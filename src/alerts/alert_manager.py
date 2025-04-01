import logging
from typing import Dict, Any, List
import json
import asyncio
from datetime import datetime
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AlertConfig:
    severity_thresholds: Dict[str, float]
    notification_endpoints: Dict[str, str]
    cooldown_period: int  # minutes
    alert_history_size: int

class AlertManager:
    def __init__(self, config: AlertConfig):
        self.config = config
        self.alert_history = []
        self.last_alert_times = {}  # Track last alert time per endpoint

    async def process_anomalies(self, anomalies: List[Dict[str, Any]]):
        """Process detected anomalies and generate alerts if necessary"""
        for anomaly in anomalies:
            if self._should_alert(anomaly):
                await self._generate_alert(anomaly)
                self._update_alert_history(anomaly)

    def _should_alert(self, anomaly: Dict[str, Any]) -> bool:
        """Determine if an alert should be generated based on severity and cooldown"""
        endpoint = anomaly.get("api_endpoint", "unknown")
        severity = anomaly.get("severity", "LOW")
        current_time = datetime.utcnow()

        # Check cooldown period
        if endpoint in self.last_alert_times:
            time_since_last_alert = (current_time - self.last_alert_times[endpoint]).total_seconds() / 60
            if time_since_last_alert < self.config.cooldown_period:
                return False

        # Check severity threshold
        return float(anomaly.get("anomaly_score", 0)) <= self.config.severity_thresholds.get(severity, -0.5)

    async def _generate_alert(self, anomaly: Dict[str, Any]):
        """Generate and send alert for the detected anomaly"""
        alert = self._create_alert_payload(anomaly)
        
        # Send alerts to configured endpoints
        for channel, endpoint in self.config.notification_endpoints.items():
            try:
                await self._send_alert(endpoint, alert)
                logger.info(f"Alert sent successfully to {channel}")
            except Exception as e:
                logger.error(f"Failed to send alert to {channel}: {str(e)}")

        # Update last alert time
        self.last_alert_times[anomaly.get("api_endpoint", "unknown")] = datetime.utcnow()

    def _create_alert_payload(self, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured alert payload"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": anomaly.get("severity", "LOW"),
            "anomaly_score": anomaly.get("anomaly_score", 0),
            "api_endpoint": anomaly.get("api_endpoint", "unknown"),
            "metrics": anomaly.get("metrics", {}),
            "description": self._generate_alert_description(anomaly),
            "recommendations": self._generate_recommendations(anomaly)
        }

    def _generate_alert_description(self, anomaly: Dict[str, Any]) -> str:
        """Generate a human-readable description of the anomaly"""
        metrics = anomaly.get("metrics", {})
        return (
            f"Anomaly detected in API {anomaly.get('api_endpoint', 'unknown')} "
            f"with severity {anomaly.get('severity', 'LOW')}. "
            f"Response time: {metrics.get('response_time', 0):.2f}ms, "
            f"Error rate: {metrics.get('error_rate', 0)*100:.2f}%, "
            f"Request rate: {metrics.get('request_rate', 0)} req/min"
        )

    def _generate_recommendations(self, anomaly: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on the anomaly type and severity"""
        recommendations = []
        metrics = anomaly.get("metrics", {})
        
        if metrics.get("response_time", 0) > 1000:  # High response time
            recommendations.extend([
                "Check for database query performance issues",
                "Review API endpoint caching strategy",
                "Monitor system resource utilization"
            ])
            
        if metrics.get("error_rate", 0) > 0.1:  # High error rate
            recommendations.extend([
                "Review error logs for specific error patterns",
                "Check downstream service dependencies",
                "Verify API input validation"
            ])
            
        if metrics.get("request_rate", 0) > 1000:  # High request rate
            recommendations.extend([
                "Consider implementing rate limiting",
                "Review and optimize caching strategy",
                "Scale up resources if needed"
            ])
            
        return recommendations

    async def _send_alert(self, endpoint: str, alert: Dict[str, Any]):
        """Send alert to notification endpoint"""
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=alert) as response:
                if response.status >= 400:
                    raise Exception(f"Failed to send alert: HTTP {response.status}")

    def _update_alert_history(self, anomaly: Dict[str, Any]):
        """Update alert history with new alert"""
        self.alert_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "anomaly": anomaly
        })
        
        # Maintain history size
        if len(self.alert_history) > self.config.alert_history_size:
            self.alert_history = self.alert_history[-self.config.alert_history_size:]

    def get_alert_history(self) -> List[Dict[str, Any]]:
        """Get alert history"""
        return self.alert_history

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get statistics about generated alerts"""
        return {
            "total_alerts": len(self.alert_history),
            "alerts_by_severity": self._count_alerts_by_severity(),
            "alerts_by_endpoint": self._count_alerts_by_endpoint()
        }

    def _count_alerts_by_severity(self) -> Dict[str, int]:
        """Count alerts by severity level"""
        severity_counts = {}
        for alert in self.alert_history:
            severity = alert["anomaly"].get("severity", "LOW")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        return severity_counts

    def _count_alerts_by_endpoint(self) -> Dict[str, int]:
        """Count alerts by API endpoint"""
        endpoint_counts = {}
        for alert in self.alert_history:
            endpoint = alert["anomaly"].get("api_endpoint", "unknown")
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
        return endpoint_counts

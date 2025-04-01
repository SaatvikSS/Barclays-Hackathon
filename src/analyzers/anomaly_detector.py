import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self, contamination: float = 0.1):
        self.isolation_forest = IsolationForest(contamination=contamination, random_state=42)
        self.scaler = StandardScaler()
        self.training_data = None
        self.feature_columns = ['response_time', 'error_rate', 'request_rate']

    def prepare_features(self, logs: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare features from raw logs"""
        df = pd.DataFrame(logs)
        
        # Calculate metrics per minute
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Resample to minute intervals
        metrics = pd.DataFrame()
        metrics['response_time'] = df['response_time'].resample('1min').mean()
        metrics['error_rate'] = (df['status_code'] >= 400).resample('1min').mean()
        metrics['request_rate'] = df['endpoint'].resample('1min').count()
        
        return metrics.fillna(0)

    def train(self, historical_logs: List[Dict[str, Any]]):
        """Train the anomaly detection model"""
        if not historical_logs:
            logger.warning("No historical logs provided for training")
            return

        try:
            features_df = self.prepare_features(historical_logs)
            self.training_data = features_df.copy()
            
            # Scale the features
            scaled_features = self.scaler.fit_transform(features_df[self.feature_columns])
            
            # Train the model
            self.isolation_forest.fit(scaled_features)
            logger.info("Successfully trained anomaly detection model")
            
        except Exception as e:
            logger.error(f"Error training anomaly detection model: {str(e)}")

    def detect_anomalies(self, current_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in current logs"""
        if not current_logs:
            return []

        try:
            features_df = self.prepare_features(current_logs)
            scaled_features = self.scaler.transform(features_df[self.feature_columns])
            
            # Predict anomalies
            predictions = self.isolation_forest.predict(scaled_features)
            anomaly_scores = self.isolation_forest.score_samples(scaled_features)
            
            # Prepare anomaly results
            anomalies = []
            for idx, (pred, score) in enumerate(zip(predictions, anomaly_scores)):
                if pred == -1:  # Anomaly detected
                    timestamp = features_df.index[idx]
                    metrics = features_df.iloc[idx]
                    
                    anomaly = {
                        "timestamp": timestamp.isoformat(),
                        "anomaly_score": float(score),
                        "metrics": {
                            "response_time": float(metrics["response_time"]),
                            "error_rate": float(metrics["error_rate"]),
                            "request_rate": float(metrics["request_rate"])
                        },
                        "severity": self._calculate_severity(score)
                    }
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return []

    def _calculate_severity(self, anomaly_score: float) -> str:
        """Calculate severity level based on anomaly score"""
        if anomaly_score < -0.8:
            return "CRITICAL"
        elif anomaly_score < -0.6:
            return "HIGH"
        elif anomaly_score < -0.4:
            return "MEDIUM"
        else:
            return "LOW"

    def predict_future_anomalies(self, window_size: int = 60) -> List[Dict[str, Any]]:
        """Predict potential future anomalies based on current trends"""
        if self.training_data is None or len(self.training_data) < window_size:
            return []

        try:
            # Create a simple forecast using rolling statistics
            forecast_df = self.training_data.copy()
            for col in self.feature_columns:
                forecast_df[f'{col}_forecast'] = forecast_df[col].rolling(window=window_size).mean()
            
            # Get the last window_size records for prediction
            recent_data = forecast_df.tail(window_size)
            
            # Calculate trend
            trends = {}
            for col in self.feature_columns:
                trend = recent_data[col].diff().mean()
                trends[col] = trend
            
            # Predict next hour
            predictions = []
            last_timestamp = recent_data.index[-1]
            
            for i in range(6):  # Predict next 6 10-minute intervals
                future_timestamp = last_timestamp + timedelta(minutes=(i+1)*10)
                predicted_values = {}
                
                for col in self.feature_columns:
                    predicted_values[col] = float(recent_data[col].iloc[-1] + trends[col] * (i+1))
                
                predictions.append({
                    "timestamp": future_timestamp.isoformat(),
                    "predicted_metrics": predicted_values,
                    "confidence": max(0, 1 - (i * 0.15))  # Confidence decreases with time
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting future anomalies: {str(e)}")
            return []

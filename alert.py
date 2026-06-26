"""
Alert system for notifications.
"""
import json
import aiohttp
from typing import List, Dict
from loguru import logger
from src.config import settings

class AlertSystem:
    """Sends alerts for anomalies."""
    
    def __init__(self):
        self.slack_webhook = settings.SLACK_WEBHOOK_URL
    
    async def send_alert(self, message: str, severity: str = "warning"):
        """Send alert through configured channels."""
        logger.info(f"Alert ({severity}): {message}")
        
        if self.slack_webhook:
            await self._send_slack_alert(message, severity)
    
    async def _send_slack_alert(self, message: str, severity: str):
        """Send alert to Slack."""
        colors = {"info": "#36a64f", "warning": "#ffa500", "critical": "#ff0000"}
        payload = {
            "attachments": [{
                "color": colors.get(severity, "#808080"),
                "text": message,
                "fields": [
                    {"title": "Severity", "value": severity.upper(), "short": True}
                ]
            }]
        }
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(self.slack_webhook, json=payload)
            logger.info("✅ Slack alert sent")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")
    
    async def send_batch_alert(self, anomalies: List[Dict]):
        """Send summary alert for multiple anomalies."""
        if not anomalies:
            return
        
        symbol_counts = {}
        for anomaly in anomalies:
            symbol = anomaly.get("symbol", "unknown")
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        message = "Anomalies Detected:\n"
        for symbol, count in symbol_counts.items():
            message += f"- {symbol}: {count} anomalies\n"
        
        await self.send_alert(message, severity="warning")
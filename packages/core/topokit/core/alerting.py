"""Alert management system for TopoKit with multi-channel alerting and escalation."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Callable, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field
from .logging import get_logger


logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"   # Immediate attention required
    HIGH = "high"           # High priority issue
    MEDIUM = "medium"       # Medium priority issue
    LOW = "low"            # Low priority issue
    INFO = "info"           # Informational


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"       # Alert is active
    ACKNOWLEDGED = "acknowledged"  # Alert has been acknowledged
    RESOLVED = "resolved"   # Alert has been resolved
    SUPPRESSED = "suppressed"  # Alert is suppressed


class AlertChannel(str, Enum):
    """Alert notification channels."""
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"
    CONSOLE = "console"  # For development/testing


@dataclass
class AlertThreshold:
    """Alert threshold configuration."""
    metric_name: str
    threshold_value: float
    comparison: str  # 'gt', 'lt', 'eq', 'gte', 'lte'
    severity: AlertSeverity
    duration_seconds: int = 60  # Duration threshold must be exceeded
    enabled: bool = True


@dataclass
class AlertRule:
    """Alert rule configuration."""
    id: str
    name: str
    description: str
    thresholds: List[AlertThreshold]
    channels: List[AlertChannel]
    enabled: bool = True
    tags: Dict[str, str] = field(default_factory=dict)


class Alert(BaseModel):
    """Alert model."""
    id: str = Field(..., description="Unique alert identifier")
    rule_id: Optional[str] = Field(default=None, description="Associated alert rule ID")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    severity: AlertSeverity = Field(..., description="Alert severity")
    status: AlertStatus = Field(default=AlertStatus.ACTIVE, description="Alert status")
    metric_name: Optional[str] = Field(default=None, description="Associated metric name")
    metric_value: Optional[float] = Field(default=None, description="Metric value that triggered alert")
    threshold_value: Optional[float] = Field(default=None, description="Threshold that was exceeded")
    source: str = Field(default="topokit", description="Alert source")
    deployment_id: Optional[str] = Field(default=None, description="Associated deployment ID")
    node_id: Optional[str] = Field(default=None, description="Associated node ID")
    tags: Dict[str, str] = Field(default_factory=dict, description="Alert tags")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Alert creation time")
    acknowledged_at: Optional[datetime] = Field(default=None, description="Acknowledgment time")
    resolved_at: Optional[datetime] = Field(default=None, description="Resolution time")
    acknowledged_by: Optional[str] = Field(default=None, description="User who acknowledged")
    resolved_by: Optional[str] = Field(default=None, description="User who resolved")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def acknowledge(self, user: str) -> None:
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = user

    def resolve(self, user: str) -> None:
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        self.resolved_by = user

    def suppress(self) -> None:
        """Suppress the alert."""
        self.status = AlertStatus.SUPPRESSED


class AlertNotifier(ABC):
    """Abstract base class for alert notifiers."""

    @abstractmethod
    async def send_alert(self, alert: Alert) -> bool:
        """Send an alert notification."""
        pass

    @abstractmethod
    def supports_channel(self, channel: AlertChannel) -> bool:
        """Check if this notifier supports a channel."""
        pass


class SlackNotifier(AlertNotifier):
    """Slack alert notifier."""

    def __init__(self, webhook_url: str):
        """Initialize Slack notifier."""
        self.webhook_url = webhook_url

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": f"*{alert.title}*",
                    "attachments": [
                        {
                            "color": self._get_color(alert.severity),
                            "fields": [
                                {"title": "Severity", "value": alert.severity.value, "short": True},
                                {"title": "Status", "value": alert.status.value, "short": True},
                                {"title": "Message", "value": alert.message, "short": False},
                            ],
                            "ts": int(alert.created_at.timestamp()),
                        }
                    ],
                }
                
                if alert.metric_name:
                    payload["attachments"][0]["fields"].append({
                        "title": "Metric",
                        "value": f"{alert.metric_name}: {alert.metric_value}",
                        "short": True,
                    })
                
                if alert.deployment_id:
                    payload["attachments"][0]["fields"].append({
                        "title": "Deployment",
                        "value": alert.deployment_id,
                        "short": True,
                    })

                async with session.post(self.webhook_url, json=payload) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    def supports_channel(self, channel: AlertChannel) -> bool:
        """Check if supports Slack channel."""
        return channel == AlertChannel.SLACK

    def _get_color(self, severity: AlertSeverity) -> str:
        """Get color for severity."""
        colors = {
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.HIGH: "warning",
            AlertSeverity.MEDIUM: "warning",
            AlertSeverity.LOW: "good",
            AlertSeverity.INFO: "good",
        }
        return colors.get(severity, "good")


class EmailNotifier(AlertNotifier):
    """Email alert notifier."""

    def __init__(self, smtp_server: str, smtp_port: int, from_email: str, to_emails: List[str]):
        """Initialize email notifier."""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.to_emails = to_emails

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via email."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"

            body = f"""
Alert Title: {alert.title}
Severity: {alert.severity.value}
Status: {alert.status.value}
Message: {alert.message}

Created: {alert.created_at}
Source: {alert.source}
"""
            if alert.metric_name:
                body += f"Metric: {alert.metric_name} = {alert.metric_value}\n"
            if alert.deployment_id:
                body += f"Deployment: {alert.deployment_id}\n"
            if alert.node_id:
                body += f"Node: {alert.node_id}\n"

            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.send_message(msg)
            
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def supports_channel(self, channel: AlertChannel) -> bool:
        """Check if supports email channel."""
        return channel == AlertChannel.EMAIL


class WebhookNotifier(AlertNotifier):
    """Webhook alert notifier."""

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        """Initialize webhook notifier."""
        self.webhook_url = webhook_url
        self.headers = headers or {}

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via webhook."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "alert_id": alert.id,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "created_at": alert.created_at.isoformat(),
                    "source": alert.source,
                    "metadata": alert.metadata,
                }
                
                if alert.metric_name:
                    payload["metric"] = {
                        "name": alert.metric_name,
                        "value": alert.metric_value,
                        "threshold": alert.threshold_value,
                    }
                
                if alert.deployment_id:
                    payload["deployment_id"] = alert.deployment_id
                
                if alert.node_id:
                    payload["node_id"] = alert.node_id

                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    return response.status in [200, 201, 204]
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False

    def supports_channel(self, channel: AlertChannel) -> bool:
        """Check if supports webhook channel."""
        return channel == AlertChannel.WEBHOOK


class ConsoleNotifier(AlertNotifier):
    """Console alert notifier (for development/testing)."""

    async def send_alert(self, alert: Alert) -> bool:
        """Print alert to console."""
        logger.warning(
            f"[ALERT] {alert.severity.value.upper()}: {alert.title} - {alert.message}"
        )
        return True

    def supports_channel(self, channel: AlertChannel) -> bool:
        """Check if supports console channel."""
        return channel == AlertChannel.CONSOLE


class AlertManager:
    """Alert management system."""

    def __init__(self):
        """Initialize alert manager."""
        self.alerts: Dict[str, Alert] = {}
        self.rules: Dict[str, AlertRule] = {}
        self.notifiers: List[AlertNotifier] = []
        self.metric_history: Dict[str, List[tuple[datetime, float]]] = {}
        self._lock = asyncio.Lock()

    def add_notifier(self, notifier: AlertNotifier) -> None:
        """Add an alert notifier."""
        self.notifiers.append(notifier)
        logger.info(f"Added alert notifier: {type(notifier).__name__}")

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self.rules[rule.id] = rule
        try:
            logger.info(f"Added alert rule: {rule.name}")
        except Exception:
            # Fallback if logger has issues
            print(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_id: str) -> None:
        """Remove an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")

    async def evaluate_threshold(self, metric_name: str, value: float, deployment_id: Optional[str] = None) -> List[Alert]:
        """Evaluate metric against alert thresholds."""
        async with self._lock:
            # Store metric history
            if metric_name not in self.metric_history:
                self.metric_history[metric_name] = []
            self.metric_history[metric_name].append((datetime.utcnow(), value))
            
            # Keep only recent history (last hour)
            cutoff = datetime.utcnow() - timedelta(hours=1)
            self.metric_history[metric_name] = [
                (ts, val) for ts, val in self.metric_history[metric_name]
                if ts > cutoff
            ]

            triggered_alerts: List[Alert] = []

            # Check all rules for this metric
            for rule in self.rules.values():
                if not rule.enabled:
                    continue

                for threshold in rule.thresholds:
                    if threshold.metric_name != metric_name or not threshold.enabled:
                        continue

                    # Check if threshold is exceeded
                    if self._check_threshold(value, threshold):
                        # Check duration requirement
                        if self._check_duration(metric_name, threshold):
                            alert = await self._create_alert(
                                rule=rule,
                                threshold=threshold,
                                metric_name=metric_name,
                                metric_value=value,
                                deployment_id=deployment_id,
                            )
                            
                            # Check if alert already exists (deduplication)
                            if alert.id not in self.alerts or self.alerts[alert.id].status == AlertStatus.RESOLVED:
                                self.alerts[alert.id] = alert
                                triggered_alerts.append(alert)
                                
                                # Send notifications
                                await self._send_notifications(alert, rule.channels)

            return triggered_alerts

    def _check_threshold(self, value: float, threshold: AlertThreshold) -> bool:
        """Check if value exceeds threshold."""
        if threshold.comparison == "gt":
            return value > threshold.threshold_value
        elif threshold.comparison == "lt":
            return value < threshold.threshold_value
        elif threshold.comparison == "eq":
            return value == threshold.threshold_value
        elif threshold.comparison == "gte":
            return value >= threshold.threshold_value
        elif threshold.comparison == "lte":
            return value <= threshold.threshold_value
        return False

    def _check_duration(self, metric_name: str, threshold: AlertThreshold) -> bool:
        """Check if threshold exceeded for required duration."""
        if threshold.duration_seconds <= 0:
            return True
        
        if metric_name not in self.metric_history:
            return False
        
        cutoff = datetime.utcnow() - timedelta(seconds=threshold.duration_seconds)
        recent_values = [
            val for ts, val in self.metric_history[metric_name]
            if ts > cutoff
        ]
        
        if not recent_values:
            return False
        
        # Check if all recent values exceed threshold
        return all(self._check_threshold(val, threshold) for val in recent_values)

    async def _create_alert(
        self,
        rule: AlertRule,
        threshold: AlertThreshold,
        metric_name: str,
        metric_value: float,
        deployment_id: Optional[str] = None,
    ) -> Alert:
        """Create an alert from rule and threshold."""
        alert_id = f"alert-{datetime.utcnow().timestamp()}-{rule.id}"
        
        title = f"{rule.name}: {metric_name} threshold exceeded"
        message = f"{metric_name} = {metric_value} {threshold.comparison} {threshold.threshold_value} (threshold: {threshold.threshold_value})"
        
        return Alert(
            id=alert_id,
            rule_id=rule.id,
            title=title,
            message=message,
            severity=threshold.severity,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold_value=threshold.threshold_value,
            deployment_id=deployment_id,
            tags=rule.tags,
        )

    async def _send_notifications(self, alert: Alert, channels: List[AlertChannel]) -> None:
        """Send alert notifications via configured channels."""
        for channel in channels:
            for notifier in self.notifiers:
                if notifier.supports_channel(channel):
                    try:
                        success = await notifier.send_alert(alert)
                        if success:
                            try:
                                logger.info(f"Sent alert {alert.id} via {channel.value}")
                            except Exception:
                                pass
                        else:
                            try:
                                logger.warning(f"Failed to send alert {alert.id} via {channel.value}")
                            except Exception:
                                pass
                    except Exception as e:
                        logger.error(f"Error sending alert via {channel.value}: {e}")

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get all active alerts, optionally filtered by severity."""
        alerts = [a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        return self.alerts.get(alert_id)

    async def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert."""
        alert = self.alerts.get(alert_id)
        if alert and alert.status == AlertStatus.ACTIVE:
            alert.acknowledge(user)
            return True
        return False

    async def resolve_alert(self, alert_id: str, user: str) -> bool:
        """Resolve an alert."""
        alert = self.alerts.get(alert_id)
        if alert:
            alert.resolve(user)
            return True
        return False

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        total = len(self.alerts)
        active = len(self.get_active_alerts())
        by_severity = {}
        for severity in AlertSeverity:
            count = len(self.get_active_alerts(severity))
            by_severity[severity.value] = count
        
        return {
            "total_alerts": total,
            "active_alerts": active,
            "by_severity": by_severity,
            "rules_count": len(self.rules),
            "notifiers_count": len(self.notifiers),
        }


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


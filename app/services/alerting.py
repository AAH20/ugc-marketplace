"""Anomaly detection and alerting service."""
from __future__ import annotations

from app.models.alert import AlertSeverity, AlertType


class AlertingService:
    """Detect anomalies in campaign metrics and generate alerts."""

    def __init__(
        self,
        spend_spike_threshold: float = 2.0,
        ctr_drop_threshold: float = 0.5,
        min_roas_threshold: float = 2.0,
    ):
        self.spend_spike_threshold = spend_spike_threshold
        self.ctr_drop_threshold = ctr_drop_threshold
        self.min_roas_threshold = min_roas_threshold

    def detect_spend_spike(
        self,
        current_spend: float,
        avg_spend: float,
        campaign_id: int,
    ) -> list[dict]:
        """Detect if current spend exceeds threshold multiple of average."""
        if avg_spend <= 0:
            return []
        ratio = current_spend / avg_spend
        if ratio >= self.spend_spike_threshold:
            severity = AlertSeverity.CRITICAL if ratio >= 10. else AlertSeverity.HIGH
            return [{
                "campaign_id": campaign_id,
                "alert_type": AlertType.SPEND_SPIKE,
                "severity": severity,
                "message": f"Spend spike detected: ${current_spend:.2f} "
                f"({ratio:.1f}x average of ${avg_spend:.2f})",
                "metric_value": current_spend,
                "threshold": avg_spend * self.spend_spike_threshold,
            }]
        return []

    def detect_ctr_drop(
        self,
        current_ctr: float,
        baseline_ctr: float,
        campaign_id: int,
    ) -> list[dict]:
        """Detect if CTR has dropped significantly from baseline."""
        if baseline_ctr <= 0:
            return []
        drop_ratio = (baseline_ctr - current_ctr) / baseline_ctr
        if drop_ratio >= self.ctr_drop_threshold:
            severity = AlertSeverity.HIGH if drop_ratio >= 0.90 else AlertSeverity.MEDIUM
            return [{
                "campaign_id": campaign_id,
                "alert_type": AlertType.CTR_DROP,
                "severity": severity,
                "message": f"CTR dropped {drop_ratio:.0%} from baseline "
                f"({baseline_ctr:.4f} → {current_ctr:.4f})",
                "metric_value": current_ctr,
                "threshold": baseline_ctr * (1 - self.ctr_drop_threshold),
            }]
        return []

    def detect_low_roas(
        self,
        current_roas: float,
        target_roas: float,
        campaign_id: int,
    ) -> list[dict]:
        """Detect if ROAS is below target threshold."""
        if current_roas >= target_roas:
            return []
        gap_ratio = (target_roas - current_roas) / target_roas if target_roas > 0 else 0
        severity = AlertSeverity.CRITICAL if gap_ratio >= 0.75 else AlertSeverity.HIGH
        return [{
            "campaign_id": campaign_id,
            "alert_type": AlertType.LOW_ROAS,
            "severity": severity,
            "message": f"ROAS {current_roas:.2f} below target {target_roas:.2f} "
            f"(gap: {gap_ratio:.0%})",
            "metric_value": current_roas,
            "threshold": target_roas,
        }]

    def detect_all(
        self,
        campaign_id: int,
        current_spend: float,
        avg_spend: float,
        current_ctr: float,
        baseline_ctr: float,
        current_roas: float,
        target_roas: float,
    ) -> list[dict]:
        """Run all anomaly detectors and return combined alerts."""
        alerts = []
        alerts.extend(self.detect_spend_spike(current_spend, avg_spend, campaign_id))
        alerts.extend(self.detect_ctr_drop(current_ctr, baseline_ctr, campaign_id))
        alerts.extend(self.detect_low_roas(current_roas, target_roas, campaign_id))
        return alerts

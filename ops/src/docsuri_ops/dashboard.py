from __future__ import annotations

from dataclasses import dataclass

from docsuri_ops.domain.enums import IncidentClass
from docsuri_ops.domain.models import (
    ClassifiedIncidentRecord,
    DashboardWindow,
    OpsDashboardView,
)


@dataclass(slots=True)
class OpsDashboardService:
    incident_store: object
    cost_guard: object | None = None
    health_service: object | None = None

    def get_dashboard(self, window: DashboardWindow) -> OpsDashboardView:
        incidents = self.list_incidents(window=window)
        alerts = [
            alert
            for alert in self.incident_store.list_alerts()
            if window.contains(alert.timestamp)
        ]
        cost_state = self.cost_guard.get_budget_state() if self.cost_guard else None
        health = self.health_service.shallow_check() if self.health_service else None
        return OpsDashboardView(
            window=window,
            incident_count=len(incidents),
            alert_count=len(alerts),
            cost_state=cost_state,
            health=health,
        )

    def list_incidents(
        self,
        *,
        window: DashboardWindow | None = None,
        incident_class: IncidentClass | None = None,
    ) -> list[ClassifiedIncidentRecord]:
        incidents = self.incident_store.list_incidents()
        if window is not None:
            incidents = [
                incident for incident in incidents if window.contains(incident.timestamp)
            ]
        if incident_class is not None:
            incidents = [
                incident
                for incident in incidents
                if incident.incident_class == incident_class
            ]
        return incidents

    def summarize_by_class(self, window: DashboardWindow) -> dict[str, int]:
        summary = {incident_class.value: 0 for incident_class in IncidentClass}
        for incident in self.list_incidents(window=window):
            summary[incident.incident_class.value] += 1
        return summary

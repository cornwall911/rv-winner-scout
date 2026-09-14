"""Health monitoring and telemetry accumulator for audit reporting."""

from datetime import datetime, timezone
from typing import List, Optional
from rv_winner_scout.domain.enums import RunStatus
from rv_winner_scout.domain.models import RunHealthReport


class HealthMonitor:
    """Collects runtime operational statistics and generates the concluding health report."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.start_time = datetime.now(timezone.utc)
        self.products_discovered = 0
        self.products_verified = 0
        self.products_rejected = 0
        self.ai_calls = 0
        self.ai_failures = 0
        self.walmart_searches = 0
        self.walmart_failures = 0
        self.failed_sources: List[str] = []
        self.circuit_breakers_tripped: List[str] = []
        self.rows_written = 0
        self.duplicates_prevented = 0
        self.degraded_components: List[str] = []
        self.fatal_failure_reason: Optional[str] = None

    def record_failed_source(self, source_url: str, failure_detail: str) -> None:
        entry = f"{source_url} -> {failure_detail}"
        if entry not in self.failed_sources:
            self.failed_sources.append(entry)

    def record_circuit_trip(self, provider_name: str) -> None:
        if provider_name not in self.circuit_breakers_tripped:
            self.circuit_breakers_tripped.append(provider_name)
        if provider_name not in self.degraded_components:
            self.degraded_components.append(provider_name)

    def mark_degraded(self, component_name: str) -> None:
        if component_name not in self.degraded_components:
            self.degraded_components.append(component_name)

    def set_fatal_failure(self, reason: str) -> None:
        self.fatal_failure_reason = reason

    def build_report(self) -> RunHealthReport:
        end_time = datetime.now(timezone.utc)

        # Determine Run Status
        if self.fatal_failure_reason:
            status = RunStatus.FAILED
        elif self.failed_sources or self.circuit_breakers_tripped or self.degraded_components:
            status = RunStatus.PARTIAL
        else:
            status = RunStatus.SUCCESS

        return RunHealthReport(
            run_id=self.run_id,
            start_time=self.start_time,
            end_time=end_time,
            status=status,
            products_discovered=self.products_discovered,
            products_verified=self.products_verified,
            products_rejected=self.products_rejected,
            ai_calls=self.ai_calls,
            ai_failures=self.ai_failures,
            walmart_searches=self.walmart_searches,
            walmart_failures=self.walmart_failures,
            failed_sources=self.failed_sources,
            circuit_breakers_tripped=self.circuit_breakers_tripped,
            rows_written=self.rows_written,
            duplicates_prevented=self.duplicates_prevented,
            degraded_components=self.degraded_components,
            failure_reason=self.fatal_failure_reason,
        )

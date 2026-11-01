from uuid import UUID

from src.modules.crm.application.ports.analytics_repository import (
    AnalyticsRepository,
    AnalyticsSummary,
)


class AnalyticsSummaryUseCase:
    def __init__(self, repository: AnalyticsRepository):
        self.repository = repository

    async def execute(self, tenant_id: UUID) -> AnalyticsSummary:
        return await self.repository.summary(tenant_id)

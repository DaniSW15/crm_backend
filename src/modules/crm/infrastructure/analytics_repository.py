from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.ports.analytics_repository import (
    AnalyticsRepository,
    AnalyticsSummary,
    CurrencyAmounts,
)
from src.modules.crm.infrastructure.models import AccountModel, DealModel


class SqlAlchemyAnalyticsRepository(AnalyticsRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def summary(self, tenant_id: UUID) -> AnalyticsSummary:
        customer_result = await self.session.execute(
            select(func.count()).select_from(AccountModel).where(
                AccountModel.tenant_id == tenant_id,
                AccountModel.is_deleted.is_(False),
            )
        )
        summary = AnalyticsSummary(total_customers=customer_result.scalar_one())
        deal_result = await self.session.execute(
            select(
                DealModel.currency,
                DealModel.status,
                func.count(),
                func.sum(DealModel.amount),
            ).where(
                DealModel.tenant_id == tenant_id,
                DealModel.is_deleted.is_(False),
            ).group_by(DealModel.currency, DealModel.status)
        )
        currencies: dict[str, CurrencyAmounts] = {}
        for currency, status, count, total in deal_result.all():
            amount = Decimal(total or "0.00")
            currency_amounts = currencies.setdefault(currency, CurrencyAmounts(currency=currency))
            summary.total_opportunities += count
            currency_amounts.total_amount += amount
            if status == "OPEN":
                summary.open_opportunities += count
                currency_amounts.open_amount += amount
            elif status == "WON":
                summary.won_opportunities += count
                currency_amounts.won_amount += amount
            elif status == "LOST":
                summary.lost_opportunities += count
                currency_amounts.lost_amount += amount
        summary.amounts_by_currency = [currencies[currency] for currency in sorted(currencies)]
        return summary

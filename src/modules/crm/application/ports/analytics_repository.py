from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID


@dataclass
class CurrencyAmounts:
    currency: str
    open_amount: Decimal = Decimal("0.00")
    won_amount: Decimal = Decimal("0.00")
    lost_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")


@dataclass
class AnalyticsSummary:
    total_customers: int = 0
    total_opportunities: int = 0
    open_opportunities: int = 0
    won_opportunities: int = 0
    lost_opportunities: int = 0
    amounts_by_currency: list[CurrencyAmounts] = field(default_factory=list)


class AnalyticsRepository(ABC):
    @abstractmethod
    async def summary(self, tenant_id: UUID) -> AnalyticsSummary:
        """Resume datos vigentes del tenant y mantiene los importes por moneda."""
        pass

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CurrencyAmountsResponse(BaseModel):
    currency: str
    open_amount: Decimal
    won_amount: Decimal
    lost_amount: Decimal
    total_amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class AnalyticsSummaryResponse(BaseModel):
    total_customers: int
    total_opportunities: int
    open_opportunities: int
    won_opportunities: int
    lost_opportunities: int
    amounts_by_currency: list[CurrencyAmountsResponse]

    model_config = ConfigDict(from_attributes=True)

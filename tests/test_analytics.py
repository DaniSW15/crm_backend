import unittest
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from test_transactions import AsyncSessionAdapter
from src.modules.crm.application.use_cases.analytics_summary import AnalyticsSummaryUseCase
from src.modules.crm.infrastructure.analytics_repository import SqlAlchemyAnalyticsRepository
from src.modules.crm.infrastructure.models import AccountModel, DealModel, PipelineModel, PipelineStageModel
from src.modules.crm.presentation.analytics_schemas import AnalyticsSummaryResponse
from src.modules.identity.infrastructure.models import TenantModel, UserModel
from src.shared.infrastructure.base_model import Base


class AnalyticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.tenant_id, self.other_tenant_id = uuid4(), uuid4()
        self.ids = {}
        with Session(self.engine) as session, session.begin():
            for tenant_id in (self.tenant_id, self.other_tenant_id):
                user_id, pipeline_id, stage_id = uuid4(), uuid4(), uuid4()
                self.ids[tenant_id] = (user_id, pipeline_id, stage_id)
                session.add(TenantModel(id=tenant_id, name="Analytics test", slug=str(tenant_id)))
                session.flush()
                session.add(UserModel(
                    id=user_id, tenant_id=tenant_id, email="analytics@example.com",
                    full_name="Analytics", hashed_password="unused",
                ))
                session.add(PipelineModel(id=pipeline_id, tenant_id=tenant_id, name="Sales"))
                session.flush()
                session.add(PipelineStageModel(
                    id=stage_id, tenant_id=tenant_id, pipeline_id=pipeline_id, name="Initial",
                ))

        self.session = Session(self.engine, expire_on_commit=False, autoflush=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)
        self.use_case = AnalyticsSummaryUseCase(
            SqlAlchemyAnalyticsRepository(AsyncSessionAdapter(self.session))
        )

    def add_deal(self, session, tenant_id, currency, status, amount, is_deleted=False):
        user_id, pipeline_id, stage_id = self.ids[tenant_id]
        session.add(DealModel(
            tenant_id=tenant_id, title="Analytics deal", currency=currency, status=status,
            amount=Decimal(amount), owner_id=user_id, pipeline_id=pipeline_id, stage_id=stage_id,
            is_deleted=is_deleted,
        ))

    async def test_empty_tenant_returns_zero_counts_and_no_currencies(self):
        summary = await self.use_case.execute(self.tenant_id)
        self.assertEqual(summary.total_customers, 0)
        self.assertEqual(summary.total_opportunities, 0)
        self.assertEqual(summary.open_opportunities, 0)
        self.assertEqual(summary.won_opportunities, 0)
        self.assertEqual(summary.lost_opportunities, 0)
        self.assertEqual(summary.amounts_by_currency, [])

    async def test_summary_isolates_tenants_and_soft_deleted_rows_and_currencies(self):
        with Session(self.engine) as session, session.begin():
            session.add_all([
                AccountModel(tenant_id=self.tenant_id, name="Customer one"),
                AccountModel(tenant_id=self.tenant_id, name="Customer two"),
                AccountModel(tenant_id=self.tenant_id, name="Deleted customer", is_deleted=True),
                AccountModel(tenant_id=self.other_tenant_id, name="Other customer"),
            ])
            for currency, status, amount in (
                ("USD", "OPEN", "125.25"),
                ("USD", "OPEN", "0.10"),
                ("USD", "OPEN", "0.20"),
                ("USD", "WON", "500.50"),
                ("USD", "LOST", "75.75"),
                ("MXN", "OPEN", "1200.00"),
                ("MXN", "WON", "50.25"),
            ):
                self.add_deal(session, self.tenant_id, currency, status, amount)
            self.add_deal(session, self.tenant_id, "USD", "OPEN", "9999.00", is_deleted=True)
            self.add_deal(session, self.other_tenant_id, "EUR", "WON", "8888.00")

        summary = await self.use_case.execute(self.tenant_id)

        self.assertEqual(summary.total_customers, 2)
        self.assertEqual(summary.total_opportunities, 7)
        self.assertEqual(summary.open_opportunities, 4)
        self.assertEqual(summary.won_opportunities, 2)
        self.assertEqual(summary.lost_opportunities, 1)
        self.assertEqual([item.currency for item in summary.amounts_by_currency], ["MXN", "USD"])
        amounts = {item.currency: item for item in summary.amounts_by_currency}
        self.assertEqual(amounts["USD"].open_amount, Decimal("125.55"))
        self.assertEqual(amounts["USD"].won_amount, Decimal("500.50"))
        self.assertEqual(amounts["USD"].lost_amount, Decimal("75.75"))
        self.assertEqual(amounts["USD"].total_amount, Decimal("701.80"))
        self.assertEqual(amounts["MXN"].open_amount, Decimal("1200.00"))
        self.assertEqual(amounts["MXN"].won_amount, Decimal("50.25"))
        self.assertEqual(amounts["MXN"].lost_amount, Decimal("0.00"))
        self.assertEqual(amounts["MXN"].total_amount, Decimal("1250.25"))

    async def test_summary_serializes_money_as_decimal_strings(self):
        with Session(self.engine) as session, session.begin():
            self.add_deal(session, self.tenant_id, "USD", "OPEN", "0.10")
            self.add_deal(session, self.tenant_id, "USD", "OPEN", "0.20")

        summary = await self.use_case.execute(self.tenant_id)
        payload = AnalyticsSummaryResponse.model_validate(summary).model_dump(mode="json")

        self.assertEqual(payload["amounts_by_currency"][0]["open_amount"], "0.30")
        self.assertEqual(payload["amounts_by_currency"][0]["total_amount"], "0.30")

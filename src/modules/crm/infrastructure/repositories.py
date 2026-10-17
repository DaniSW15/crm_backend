from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.ports.deal_repository import DealRepository
from src.modules.crm.domain.entities.deal import Deal
from src.modules.crm.infrastructure.models import DealModel, DealStageHistoryModel


class SqlAlchemyDealRepository(DealRepository):
    """
    Implementación del repositorio de Deals usando SQLAlchemy 2.0 Async.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: DealModel) -> Deal:
        return Deal(
            id=model.id,
            tenant_id=model.tenant_id,
            title=model.title,
            amount=Decimal(str(model.amount)),
            currency=model.currency,
            pipeline_id=model.pipeline_id,
            stage_id=model.stage_id,
            owner_id=model.owner_id,
            status=model.status,
            account_id=model.account_id,
            contact_id=model.contact_id,
            expected_close_date=model.expected_close_date,
            actual_close_date=model.actual_close_date,
            lost_reason=model.lost_reason,
            custom_fields=model.custom_fields or {},
        )

    async def get_by_id(self, deal_id: UUID, tenant_id: UUID) -> Optional[Deal]:
        stmt = select(DealModel).where(
            DealModel.id == deal_id,
            DealModel.tenant_id == tenant_id,
            DealModel.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(
        self,
        tenant_id: UUID,
        pipeline_id: Optional[UUID] = None,
        stage_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Deal]:
        stmt = (
            select(DealModel)
            .where(
                DealModel.tenant_id == tenant_id,
                DealModel.is_deleted.is_(False),
            )
            .limit(limit)
            .offset(offset)
            .order_by(DealModel.created_at.desc())
        )

        if pipeline_id:
            stmt = stmt.where(DealModel.pipeline_id == pipeline_id)
        if stage_id:
            stmt = stmt.where(DealModel.stage_id == stage_id)
        if status:
            stmt = stmt.where(DealModel.status == status)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def save(self, deal: Deal) -> Deal:
        stmt = select(DealModel).where(
            DealModel.id == deal.id,
            DealModel.tenant_id == deal.tenant_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            # Actualización
            model.title = deal.title
            model.amount = float(deal.amount)
            model.currency = deal.currency
            model.pipeline_id = deal.pipeline_id
            model.stage_id = deal.stage_id
            model.owner_id = deal.owner_id
            model.status = deal.status
            model.account_id = deal.account_id
            model.contact_id = deal.contact_id
            model.expected_close_date = deal.expected_close_date
            model.actual_close_date = deal.actual_close_date
            model.lost_reason = deal.lost_reason
            model.custom_fields = deal.custom_fields
        else:
            # Creación
            model = DealModel(
                id=deal.id,
                tenant_id=deal.tenant_id,
                title=deal.title,
                amount=float(deal.amount),
                currency=deal.currency,
                pipeline_id=deal.pipeline_id,
                stage_id=deal.stage_id,
                owner_id=deal.owner_id,
                status=deal.status,
                account_id=deal.account_id,
                contact_id=deal.contact_id,
                expected_close_date=deal.expected_close_date,
                actual_close_date=deal.actual_close_date,
                lost_reason=deal.lost_reason,
                custom_fields=deal.custom_fields,
            )
            self.session.add(model)

        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def record_stage_history(
        self,
        tenant_id: UUID,
        deal_id: UUID,
        from_stage_id: Optional[UUID],
        to_stage_id: UUID,
        changed_by_user_id: Optional[UUID] = None,
        duration_seconds: Optional[int] = None,
    ) -> None:
        history = DealStageHistoryModel(
            tenant_id=tenant_id,
            deal_id=deal_id,
            from_stage_id=from_stage_id,
            to_stage_id=to_stage_id,
            changed_by_user_id=changed_by_user_id,
            duration_seconds=duration_seconds,
            transitioned_at=datetime.utcnow(),
        )
        self.session.add(history)
        await self.session.commit()


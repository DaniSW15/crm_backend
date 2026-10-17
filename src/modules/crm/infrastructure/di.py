from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.ports.deal_repository import DealRepository
from src.modules.crm.application.use_cases.create_deal import CreateDealUseCase
from src.modules.crm.application.use_cases.list_deals import ListDealsUseCase
from src.modules.crm.application.use_cases.move_deal_stage import MoveDealStageUseCase
from src.modules.crm.infrastructure.repositories import SqlAlchemyDealRepository


class CrmProvider(Provider):
    """
    Proveedor de inyección de dependencias (Dishka) para el módulo CRM.
    """
    scope = Scope.REQUEST

    @provide
    def get_deal_repository(self, session: AsyncSession) -> DealRepository:
        return SqlAlchemyDealRepository(session=session)

    @provide
    def get_create_deal_use_case(self, repo: DealRepository) -> CreateDealUseCase:
        return CreateDealUseCase(deal_repository=repo)

    @provide
    def get_move_deal_stage_use_case(self, repo: DealRepository) -> MoveDealStageUseCase:
        return MoveDealStageUseCase(deal_repository=repo)

    @provide
    def get_list_deals_use_case(self, repo: DealRepository) -> ListDealsUseCase:
        return ListDealsUseCase(deal_repository=repo)


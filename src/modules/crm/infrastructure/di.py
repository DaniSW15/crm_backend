from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.ports.deal_repository import DealRepository
from src.modules.crm.application.ports.pipeline_repository import PipelineRepository
from src.modules.crm.application.use_cases.create_deal import CreateDealUseCase
from src.modules.crm.application.use_cases.delete_deal import DeleteDealUseCase
from src.modules.crm.application.use_cases.list_deals import ListDealsUseCase
from src.modules.crm.application.use_cases.list_pipelines import ListPipelinesUseCase
from src.modules.crm.application.use_cases.move_deal_stage import MoveDealStageUseCase
from src.modules.crm.application.use_cases.update_deal import UpdateDealUseCase
from src.modules.crm.infrastructure.repositories import (
    SqlAlchemyDealRepository,
    SqlAlchemyPipelineRepository,
)
from src.shared.application.unit_of_work import UnitOfWork


class CrmProvider(Provider):
    """
    Proveedor de inyección de dependencias (Dishka) para el módulo CRM.
    """
    scope = Scope.REQUEST

    @provide
    def get_deal_repository(self, session: AsyncSession) -> DealRepository:
        return SqlAlchemyDealRepository(session=session)

    @provide
    def get_pipeline_repository(self, session: AsyncSession) -> PipelineRepository:
        return SqlAlchemyPipelineRepository(session=session)

    @provide
    def get_create_deal_use_case(
        self, repo: DealRepository, pipelines: PipelineRepository, uow: UnitOfWork
    ) -> CreateDealUseCase:
        return CreateDealUseCase(deal_repository=repo, pipeline_repository=pipelines, uow=uow)

    @provide
    def get_update_deal_use_case(self, repo: DealRepository, uow: UnitOfWork) -> UpdateDealUseCase:
        return UpdateDealUseCase(deal_repository=repo, uow=uow)

    @provide
    def get_move_deal_stage_use_case(
        self, repo: DealRepository, pipelines: PipelineRepository, uow: UnitOfWork
    ) -> MoveDealStageUseCase:
        return MoveDealStageUseCase(deal_repository=repo, pipeline_repository=pipelines, uow=uow)

    @provide
    def get_list_deals_use_case(self, repo: DealRepository) -> ListDealsUseCase:
        return ListDealsUseCase(deal_repository=repo)

    @provide
    def get_delete_deal_use_case(self, repo: DealRepository, uow: UnitOfWork) -> DeleteDealUseCase:
        return DeleteDealUseCase(deal_repository=repo, uow=uow)

    @provide
    def get_list_pipelines_use_case(self, repo: PipelineRepository) -> ListPipelinesUseCase:
        return ListPipelinesUseCase(pipeline_repo=repo)


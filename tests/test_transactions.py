"""Repositorios reales sobre SQLite; adaptador async solo para las pruebas.

No sustituye una prueba de integración con PostgreSQL y asyncpg.
"""
import asyncio
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from src.modules.crm.application.use_cases.create_deal import CreateDealCommand, CreateDealUseCase
from src.modules.crm.application.use_cases.delete_deal import DeleteDealUseCase
from src.modules.crm.application.use_cases.move_deal_stage import MoveDealStageCommand, MoveDealStageUseCase
from src.modules.crm.application.use_cases.update_deal import UpdateDealCommand, UpdateDealUseCase
from src.modules.crm.infrastructure.models import DealModel, DealStageHistoryModel, PipelineModel, PipelineStageModel
from src.modules.crm.infrastructure.repositories import SqlAlchemyDealRepository, SqlAlchemyPipelineRepository
from src.modules.identity.application.ports.security import PasswordHasher, TokenService
from src.modules.identity.application.use_cases.register_tenant import RegisterTenantCommand, RegisterTenantUseCase
from src.modules.identity.infrastructure.models import TenantModel, UserModel
from src.modules.identity.infrastructure.repositories import SqlAlchemyIdentityRepository
from src.shared.domain.exceptions import BusinessRuleViolationException, EntityNotFoundException
from src.shared.infrastructure.base_model import Base
from src.shared.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_type, _compiler, **_kwargs):
    return "JSON"


class AsyncTransactionAdapter:
    def __init__(self, transaction):
        self.transaction = transaction

    async def __aenter__(self):
        self.transaction.__enter__()
        return self

    async def __aexit__(self, *args):
        self.transaction.__exit__(*args)


class AsyncSessionAdapter:
    def __init__(self, session):
        self.session = session

    def begin(self):
        return AsyncTransactionAdapter(self.session.begin())

    def add(self, value):
        self.session.add(value)

    async def execute(self, statement):
        return self.session.execute(statement)

    async def flush(self):
        self.session.flush()

    async def refresh(self, value):
        self.session.refresh(value)


class TransactionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.tenant_id, self.other_tenant_id, self.user_id = uuid4(), uuid4(), uuid4()
        self.pipeline_id, self.other_pipeline_id = uuid4(), uuid4()
        self.stage_id, self.next_stage_id, self.other_stage_id = uuid4(), uuid4(), uuid4()
        with Session(self.engine) as session, session.begin():
            session.add_all([
                TenantModel(id=self.tenant_id, name="Test", slug="test"),
                TenantModel(id=self.other_tenant_id, name="Other", slug="other"),
            ])
            session.flush()
            session.add(UserModel(id=self.user_id, tenant_id=self.tenant_id,
                                  email="test@example.com", full_name="Test", hashed_password="hashed"))
            session.add_all([
                PipelineModel(id=self.pipeline_id, tenant_id=self.tenant_id, name="Sales"),
                PipelineModel(id=self.other_pipeline_id, tenant_id=self.other_tenant_id, name="Other"),
            ])
            session.flush()
            session.add_all([
                PipelineStageModel(id=self.stage_id, tenant_id=self.tenant_id,
                                   pipeline_id=self.pipeline_id, name="Initial", order=1),
                PipelineStageModel(id=self.next_stage_id, tenant_id=self.tenant_id,
                                   pipeline_id=self.pipeline_id, name="Next", order=2),
                PipelineStageModel(id=self.other_stage_id, tenant_id=self.other_tenant_id,
                                   pipeline_id=self.other_pipeline_id, name="Other", order=1),
            ])

        self.session = Session(self.engine, expire_on_commit=False, autoflush=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)
        self.db = AsyncSessionAdapter(self.session)
        self.uow = SqlAlchemyUnitOfWork(self.db)
        self.deals = SqlAlchemyDealRepository(self.db)
        self.pipelines = SqlAlchemyPipelineRepository(self.db)
        self.create = CreateDealUseCase(self.deals, self.pipelines, self.uow)
        self.move = MoveDealStageUseCase(self.deals, self.pipelines, self.uow)
        self.hasher = Mock(spec=PasswordHasher)
        self.hasher.hash.return_value = "hashed-password"
        self.tokens = Mock(spec=TokenService)
        self.tokens.create_access_token.return_value = "test-token"
        self.register = RegisterTenantUseCase(
            SqlAlchemyIdentityRepository(self.db), self.hasher, self.tokens, self.uow
        )

    def command(self, **overrides):
        fields = dict(tenant_id=self.tenant_id, title="Test opportunity", amount=Decimal("125.25"),
                      currency="USD", pipeline_id=self.pipeline_id, stage_id=self.stage_id,
                      owner_id=self.user_id)
        fields.update(overrides)
        return CreateDealCommand(**fields)

    def registration(self):
        return RegisterTenantCommand("New company", "new-company", "New Admin",
                                     "admin@new.example", "test-password")

    def count(self, model):
        with Session(self.engine) as session:
            return session.scalar(select(func.count()).select_from(model))

    def stored_stage(self, deal_id):
        with Session(self.engine) as session:
            return session.get(DealModel, deal_id).stage_id

    async def test_create_commits_deal_and_initial_history(self):
        deal = await self.create.execute(self.command())
        self.assertEqual(self.count(DealModel), 1)
        self.assertEqual(self.count(DealStageHistoryModel), 1)
        self.assertEqual(self.stored_stage(deal.id), self.stage_id)

    async def test_create_rolls_back_if_history_fails(self):
        with patch.object(self.deals, "record_stage_history", side_effect=RuntimeError("history failed")):
            with self.assertRaises(RuntimeError):
                await self.create.execute(self.command())
        self.assertEqual(self.count(DealModel), 0)
        self.assertEqual(self.count(DealStageHistoryModel), 0)

    async def test_move_commits_stage_and_history(self):
        deal = await self.create.execute(self.command())
        await self.move.execute(MoveDealStageCommand(self.tenant_id, deal.id, self.next_stage_id, self.user_id))
        self.assertEqual(self.stored_stage(deal.id), self.next_stage_id)
        self.assertEqual(self.count(DealStageHistoryModel), 2)

    async def test_move_rolls_back_when_history_foreign_key_fails(self):
        deal = await self.create.execute(self.command())
        with self.assertRaises(IntegrityError):
            await self.move.execute(MoveDealStageCommand(self.tenant_id, deal.id, self.next_stage_id, uuid4()))
        self.assertEqual(self.stored_stage(deal.id), self.stage_id)
        self.assertEqual(self.count(DealStageHistoryModel), 1)
        # La misma sesión debe poder procesar otra operación después del rollback.
        await self.move.execute(MoveDealStageCommand(self.tenant_id, deal.id, self.next_stage_id, self.user_id))
        self.assertEqual(self.stored_stage(deal.id), self.next_stage_id)

    async def test_create_rejects_foreign_tenant_pipeline(self):
        with self.assertRaises(EntityNotFoundException):
            await self.create.execute(self.command(pipeline_id=self.other_pipeline_id, stage_id=self.other_stage_id))
        self.assertEqual(self.count(DealModel), 0)

    async def test_create_rejects_stage_from_another_pipeline(self):
        with self.assertRaises(BusinessRuleViolationException):
            await self.create.execute(self.command(stage_id=self.other_stage_id))
        self.assertEqual(self.count(DealModel), 0)

    async def test_move_rejects_unknown_or_foreign_stage(self):
        deal = await self.create.execute(self.command())
        for stage_id in (uuid4(), self.other_stage_id):
            with self.subTest(stage_id=stage_id), self.assertRaises(BusinessRuleViolationException):
                await self.move.execute(MoveDealStageCommand(self.tenant_id, deal.id, stage_id))
        self.assertEqual(self.stored_stage(deal.id), self.stage_id)
        self.assertEqual(self.count(DealStageHistoryModel), 1)

    async def test_inconsistent_stage_tenant_is_rejected(self):
        # Incluso si una fila antigua tiene pipeline válido pero tenant incorrecto.
        with Session(self.engine) as session, session.begin():
            session.get(PipelineStageModel, self.next_stage_id).tenant_id = self.other_tenant_id
        with self.assertRaises(BusinessRuleViolationException):
            await self.create.execute(self.command(stage_id=self.next_stage_id))
        self.assertEqual(self.count(DealModel), 0)

    async def test_inactive_pipeline_is_rejected(self):
        with Session(self.engine) as session, session.begin():
            session.get(PipelineModel, self.pipeline_id).is_active = False
        with self.assertRaises(BusinessRuleViolationException):
            await self.create.execute(self.command())

    async def test_update_and_soft_delete_still_commit(self):
        deal = await self.create.execute(self.command())
        await UpdateDealUseCase(self.deals, self.uow).execute(
            UpdateDealCommand(deal.id, self.tenant_id, title="Updated opportunity")
        )
        with Session(self.engine) as session:
            self.assertEqual(session.get(DealModel, deal.id).title, "Updated opportunity")
        await DeleteDealUseCase(self.deals, self.uow).execute(deal.id, self.tenant_id)
        with Session(self.engine) as session:
            self.assertTrue(session.get(DealModel, deal.id).is_deleted)

    async def test_registration_commits_company_and_admin(self):
        result = await self.register.execute(self.registration())
        self.assertEqual(result.access_token, "test-token")
        self.assertEqual(self.count(TenantModel), 3)
        self.assertEqual(self.count(UserModel), 2)

    async def test_registration_rolls_back_if_user_insert_fails(self):
        self.hasher.hash.return_value = None  # Fuerza NOT NULL al insertar el usuario.
        with self.assertRaises(IntegrityError):
            await self.register.execute(self.registration())
        self.assertEqual(self.count(TenantModel), 2)
        self.assertEqual(self.count(UserModel), 1)

    async def test_commit_failure_rolls_back_all_changes(self):
        def fail_commit(_session):
            raise RuntimeError("commit failed")

        event.listen(self.session, "before_commit", fail_commit)
        with self.assertRaises(RuntimeError):
            await self.create.execute(self.command())
        self.assertEqual(self.count(DealModel), 0)
        self.assertEqual(self.count(DealStageHistoryModel), 0)

    async def test_cancellation_rolls_back_pending_changes(self):
        with self.assertRaises(asyncio.CancelledError):
            async with self.uow:
                self.session.add(TenantModel(name="Cancelled", slug="cancelled"))
                await self.db.flush()
                raise asyncio.CancelledError()
        self.assertEqual(self.count(TenantModel), 2)

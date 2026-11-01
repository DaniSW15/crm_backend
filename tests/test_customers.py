"""Clientes con repositorios reales y transacciones SQLite en memoria."""
import unittest
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

import test_transactions as transaction_helpers
from src.modules.crm.application.use_cases.customers import CreateCustomerCommand, CustomerUseCases
from src.modules.crm.infrastructure.customer_repository import SqlAlchemyCustomerRepository
from src.modules.crm.infrastructure.models import AccountModel
from src.modules.crm.presentation.customer_schemas import CustomerCreateRequest, CustomerResponse, CustomerUpdateRequest
from src.modules.identity.infrastructure.models import TenantModel, UserModel
from src.shared.domain.exceptions import BusinessRuleViolationException, EntityNotFoundException
from src.shared.infrastructure.base_model import Base
from src.shared.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


class CustomerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.tenant_id, self.other_tenant_id = uuid4(), uuid4()
        self.owner_id, self.foreign_owner_id, self.deleted_owner_id = uuid4(), uuid4(), uuid4()
        with Session(self.engine) as session, session.begin():
            session.add_all([
                TenantModel(id=self.tenant_id, name="Current", slug="current"),
                TenantModel(id=self.other_tenant_id, name="Other", slug="other"),
            ])
            session.flush()
            for user_id, tenant_id, deleted in (
                (self.owner_id, self.tenant_id, False),
                (self.foreign_owner_id, self.other_tenant_id, False),
                (self.deleted_owner_id, self.tenant_id, True),
            ):
                session.add(UserModel(
                    id=user_id, tenant_id=tenant_id, email=f"{user_id}@example.com",
                    full_name="Owner", hashed_password="unused", is_deleted=deleted,
                ))
        self.session = Session(self.engine, expire_on_commit=False, autoflush=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)
        adapter = transaction_helpers.AsyncSessionAdapter(self.session)
        self.repository = SqlAlchemyCustomerRepository(adapter)
        self.cases = CustomerUseCases(self.repository, SqlAlchemyUnitOfWork(adapter))

    def command(self, **changes):
        fields = dict(tenant_id=self.tenant_id, name="Acme Customer", owner_id=self.owner_id)
        fields.update(changes)
        return CreateCustomerCommand(**fields)

    def count(self):
        with Session(self.engine) as session:
            return session.scalar(select(func.count()).select_from(AccountModel))

    async def test_create_persists_customer_and_serializes_decimal_as_string(self):
        customer = await self.cases.create(self.command(annual_revenue=Decimal("125000.25")))
        with Session(self.engine) as session:
            stored = session.get(AccountModel, customer.id)
            self.assertEqual(stored.tenant_id, self.tenant_id)
            self.assertEqual(stored.owner_id, self.owner_id)
            self.assertEqual(stored.annual_revenue, Decimal("125000.25"))
        self.assertEqual(CustomerResponse.model_validate(customer).model_dump(mode="json")["annual_revenue"], "125000.25")

    async def test_legacy_accounts_remain_readable_and_can_be_corrected(self):
        customer_id = uuid4()
        with Session(self.engine) as session, session.begin():
            session.add(AccountModel(
                id=customer_id, tenant_id=self.tenant_id, name="A",
                annual_revenue=Decimal("-1.00"),
            ))

        customer = await self.cases.get(customer_id, self.tenant_id)
        self.assertEqual(customer.name, "A")
        self.assertEqual(customer.annual_revenue, Decimal("-1.00"))
        listed = await self.cases.list(self.tenant_id)
        self.assertEqual([item.id for item in listed], [customer_id])
        self.assertEqual(CustomerResponse.model_validate(listed[0]).name, "A")
        self.session.rollback()

        corrected = await self.cases.update(customer_id, self.tenant_id, {
            "name": "Corrected customer", "annual_revenue": Decimal("1.00"),
        })
        self.assertEqual(corrected.name, "Corrected customer")
        self.assertEqual(corrected.annual_revenue, Decimal("1.00"))

    async def test_create_commands_still_validate_domain_rules(self):
        for fields in ({"name": "A"}, {"annual_revenue": Decimal("-1.00")}):
            with self.subTest(fields=fields), self.assertRaises(BusinessRuleViolationException):
                await self.cases.create(self.command(**fields))
        self.assertEqual(self.count(), 0)

    async def test_list_is_tenant_scoped_excludes_deleted_and_paginates(self):
        first = await self.cases.create(self.command(name="First customer"))
        second = await self.cases.create(self.command(name="Second customer"))
        await self.cases.create(self.command(tenant_id=self.other_tenant_id, owner_id=self.foreign_owner_id))
        with Session(self.engine) as session, session.begin():
            session.add(AccountModel(tenant_id=self.tenant_id, name="Deleted", is_deleted=True))
        customers = await self.cases.list(self.tenant_id)
        self.assertEqual({customer.id for customer in customers}, {first.id, second.id})
        page = await self.cases.list(self.tenant_id, limit=1, offset=1)
        self.assertEqual([customer.id for customer in page], [customers[1].id])

    async def test_get_and_patch_do_not_reveal_foreign_or_deleted_customers(self):
        customer = await self.cases.create(self.command())
        with Session(self.engine) as session, session.begin():
            deleted_id = uuid4()
            session.add(AccountModel(id=deleted_id, tenant_id=self.tenant_id, name="Deleted", is_deleted=True))
        cases = [(customer.id, self.other_tenant_id), (deleted_id, self.tenant_id), (uuid4(), self.tenant_id)]
        for customer_id, tenant_id in cases:
            with self.subTest(customer_id=customer_id):
                with self.assertRaises(EntityNotFoundException):
                    await self.cases.get(customer_id, tenant_id)
                self.session.rollback()
                with self.assertRaises(EntityNotFoundException):
                    await self.cases.update(customer_id, tenant_id, {"name": "Must not persist"})
        with Session(self.engine) as session:
            self.assertEqual(session.get(AccountModel, customer.id).name, customer.name)

    async def test_patch_distinguishes_unset_fields_and_explicit_null(self):
        customer = await self.cases.create(self.command(
            phone="5551234", industry="Software", annual_revenue=Decimal("10.25"),
            custom_fields={"segment": "enterprise"},
        ))
        patch_request = CustomerUpdateRequest(phone=None, owner_id=None, annual_revenue=None)
        updated = await self.cases.update(customer.id, self.tenant_id, patch_request.model_dump(exclude_unset=True))
        self.assertIsNone(updated.phone)
        self.assertIsNone(updated.owner_id)
        self.assertIsNone(updated.annual_revenue)
        self.assertEqual(updated.name, customer.name)
        self.assertEqual(updated.industry, "Software")
        self.assertEqual(updated.custom_fields, {"segment": "enterprise"})
        with Session(self.engine) as session:
            self.assertIsNone(session.get(AccountModel, customer.id).phone)

    async def test_invalid_owners_reject_creation_without_writes(self):
        messages = []
        for owner_id in (self.foreign_owner_id, self.deleted_owner_id, uuid4()):
            with self.subTest(owner_id=owner_id):
                with self.assertRaises(BusinessRuleViolationException) as error:
                    await self.cases.create(self.command(owner_id=owner_id))
                messages.append(error.exception.message)
                self.assertEqual(self.count(), 0)
        self.assertEqual(len(set(messages)), 1)

    async def test_invalid_owners_reject_patch_without_partial_changes(self):
        customer = await self.cases.create(self.command())
        for owner_id in (self.foreign_owner_id, self.deleted_owner_id, uuid4()):
            with self.subTest(owner_id=owner_id):
                with self.assertRaises(BusinessRuleViolationException):
                    await self.cases.update(customer.id, self.tenant_id, {
                        "owner_id": owner_id, "name": "Must not persist",
                    })
                with Session(self.engine) as session:
                    stored = session.get(AccountModel, customer.id)
                    self.assertEqual(stored.name, customer.name)
                    self.assertEqual(stored.owner_id, self.owner_id)

    async def test_failure_after_flush_rolls_back_customer_creation(self):
        original_save = self.repository.save

        async def fail_after_flush(customer):
            await original_save(customer)
            raise RuntimeError("simulated operation failure")

        with patch.object(self.repository, "save", side_effect=fail_after_flush):
            with self.assertRaises(RuntimeError):
                await self.cases.create(self.command())
        self.assertEqual(self.count(), 0)
        await self.cases.create(self.command())
        self.assertEqual(self.count(), 1)

    def test_schemas_reject_tenant_injection_required_nulls_and_invalid_amounts(self):
        for payload in ({"name": None}, {"custom_fields": None}, {"tenant_id": str(self.other_tenant_id)}, {"name": "  "}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                CustomerUpdateRequest(**payload)
        for amount in ("-1.00", "NaN", "1.001", "10000000000000.00"):
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                CustomerCreateRequest(name="Acme", annual_revenue=amount)

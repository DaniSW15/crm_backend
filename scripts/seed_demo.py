import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.modules.crm.infrastructure.models import (
    AccountModel,
    ContactModel,
    PipelineModel,
    PipelineStageModel,
)
from src.modules.identity.infrastructure.models import TenantModel, UserModel

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
DEFAULT_DEV_USER_ID = uuid.UUID("d0000000-0000-0000-0000-000000000001")
DEFAULT_CLIENT_USER_ID = uuid.UUID("e0000000-0000-0000-0000-000000000001")
DEFAULT_SALES_REP_ID = uuid.UUID("c0000000-0000-0000-0000-000000000001")
DEFAULT_PIPELINE_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
DEFAULT_STAGE_1_ID = uuid.UUID("b0000000-0000-0000-0000-000000000001")
DEFAULT_STAGE_2_ID = uuid.UUID("b0000000-0000-0000-0000-000000000002")
DEFAULT_STAGE_3_ID = uuid.UUID("b0000000-0000-0000-0000-000000000003")
DEFAULT_SWAGGER_UUID = uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")


async def seed_initial_data(session: AsyncSession) -> None:
    """Inserta datos iniciales de prueba (Tenant, Usuarios, Cuentas, Contactos y Embudo) si no existen."""
    # 1. Tenant
    tenant_res = await session.execute(select(TenantModel).where(TenantModel.id == DEFAULT_TENANT_ID))
    if not tenant_res.scalar_one_or_none():
        tenant = TenantModel(
            id=DEFAULT_TENANT_ID,
            name="Organización Demo",
            slug="demo-corp",
            plan="ENTERPRISE",
        )
        session.add(tenant)
        await session.flush()

    # 2. Usuarios
    user_res = await session.execute(select(UserModel).where(UserModel.id == DEFAULT_USER_ID))
    if not user_res.scalar_one_or_none():
        user = UserModel(
            id=DEFAULT_USER_ID,
            tenant_id=DEFAULT_TENANT_ID,
            email="admin@democrm.com",
            hashed_password=hash_password("admin123"),
            full_name="Admin Demo",
            role="ADMIN",
        )
        session.add(user)

    sales_res = await session.execute(select(UserModel).where(UserModel.id == DEFAULT_SALES_REP_ID))
    if not sales_res.scalar_one_or_none():
        sales_rep = UserModel(
            id=DEFAULT_SALES_REP_ID,
            tenant_id=DEFAULT_TENANT_ID,
            email="ventas@democrm.com",
            hashed_password=hash_password("admin123"),
            full_name="Comercial Demo",
            role="SALES_REP",
        )
        session.add(sales_rep)

    dev_res = await session.execute(select(UserModel).where(UserModel.id == DEFAULT_DEV_USER_ID))
    if not dev_res.scalar_one_or_none():
        dev_user = UserModel(
            id=DEFAULT_DEV_USER_ID,
            tenant_id=DEFAULT_TENANT_ID,
            email="dev@democrm.com",
            hashed_password=hash_password("admin123"),
            full_name="Desarrollador Demo",
            role="DEV",
        )
        session.add(dev_user)

    client_res = await session.execute(select(UserModel).where(UserModel.id == DEFAULT_CLIENT_USER_ID))
    if not client_res.scalar_one_or_none():
        client_user = UserModel(
            id=DEFAULT_CLIENT_USER_ID,
            tenant_id=DEFAULT_TENANT_ID,
            email="cliente@democrm.com",
            hashed_password=hash_password("admin123"),
            full_name="Cliente Usuario Demo",
            role="CLIENTE",
        )
        session.add(client_user)
    await session.flush()

    # 3. Cuenta de prueba (Cubre el default de Swagger 3fa85f64...)
    acc_res = await session.execute(select(AccountModel).where(AccountModel.id == DEFAULT_SWAGGER_UUID))
    if not acc_res.scalar_one_or_none():
        account = AccountModel(
            id=DEFAULT_SWAGGER_UUID,
            tenant_id=DEFAULT_TENANT_ID,
            name="Acme Corporation",
            industry="Software & Tecnología",
            website="https://acme.com",
            owner_id=DEFAULT_USER_ID,
        )
        session.add(account)
        await session.flush()

    # 4. Contacto de prueba (Cubre el default de Swagger 3fa85f64...)
    cont_res = await session.execute(select(ContactModel).where(ContactModel.id == DEFAULT_SWAGGER_UUID))
    if not cont_res.scalar_one_or_none():
        contact = ContactModel(
            id=DEFAULT_SWAGGER_UUID,
            tenant_id=DEFAULT_TENANT_ID,
            account_id=DEFAULT_SWAGGER_UUID,
            first_name="Juan",
            last_name="Pérez",
            email="juan.perez@acme.com",
            job_title="Director de Operaciones",
        )
        session.add(contact)
        await session.flush()

    # 5. Pipeline y Etapas
    pipe_res = await session.execute(select(PipelineModel).where(PipelineModel.id == DEFAULT_PIPELINE_ID))
    if not pipe_res.scalar_one_or_none():
        pipeline = PipelineModel(
            id=DEFAULT_PIPELINE_ID,
            tenant_id=DEFAULT_TENANT_ID,
            name="Embudo Principal de Ventas",
            is_default=True,
        )
        session.add(pipeline)
        await session.flush()

        stages = [
            PipelineStageModel(
                id=DEFAULT_STAGE_1_ID,
                tenant_id=DEFAULT_TENANT_ID,
                pipeline_id=DEFAULT_PIPELINE_ID,
                name="Prospección",
                order=1,
                win_probability=20.0,
            ),
            PipelineStageModel(
                id=DEFAULT_STAGE_2_ID,
                tenant_id=DEFAULT_TENANT_ID,
                pipeline_id=DEFAULT_PIPELINE_ID,
                name="Demostración y Propuesta",
                order=2,
                win_probability=60.0,
            ),
            PipelineStageModel(
                id=DEFAULT_STAGE_3_ID,
                tenant_id=DEFAULT_TENANT_ID,
                pipeline_id=DEFAULT_PIPELINE_ID,
                name="Cerrado Ganado",
                order=3,
                win_probability=100.0,
                is_won_stage=True,
            ),
        ]
        session.add_all(stages)

    await session.commit()


async def main() -> None:
    from src.core.database import async_session_factory, engine
    from src.shared.infrastructure.base_model import Base

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_session_factory() as session:
            await seed_initial_data(session)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

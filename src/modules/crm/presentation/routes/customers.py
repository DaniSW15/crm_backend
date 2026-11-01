from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from src.core.tenant import TenantContext, resolve_tenant_context
from src.modules.crm.application.use_cases.customers import CreateCustomerCommand, CustomerUseCases
from src.modules.crm.presentation.customer_schemas import CustomerCreateRequest, CustomerResponse, CustomerUpdateRequest
from src.shared.domain.exceptions import BusinessRuleViolationException, EntityNotFoundException


router = APIRouter(prefix="/customers", tags=["CRM - Clientes"])


@router.get("", response_model=list[CustomerResponse], include_in_schema=False)
@router.get("/", response_model=list[CustomerResponse])
@inject
async def list_customers(
    use_cases: FromDishka[CustomerUseCases],
    tenant: TenantContext = Depends(resolve_tenant_context),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[CustomerResponse]:
    customers = await use_cases.list(tenant.tenant_id, limit, offset)
    return [CustomerResponse.model_validate(customer) for customer in customers]


@router.post("", response_model=CustomerResponse, status_code=201, include_in_schema=False)
@router.post("/", response_model=CustomerResponse, status_code=201)
@inject
async def create_customer(
    request: CustomerCreateRequest,
    use_cases: FromDishka[CustomerUseCases],
    tenant: TenantContext = Depends(resolve_tenant_context),
) -> CustomerResponse:
    try:
        customer = await use_cases.create(CreateCustomerCommand(
            tenant_id=tenant.tenant_id, **request.model_dump(),
        ))
        return CustomerResponse.model_validate(customer)
    except BusinessRuleViolationException as error:
        raise HTTPException(status_code=400, detail=error.message)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="No se pudo guardar el cliente con las referencias indicadas.")


@router.get("/{customer_id}", response_model=CustomerResponse, include_in_schema=False)
@router.get("/{customer_id}/", response_model=CustomerResponse)
@inject
async def get_customer(
    customer_id: UUID,
    use_cases: FromDishka[CustomerUseCases],
    tenant: TenantContext = Depends(resolve_tenant_context),
) -> CustomerResponse:
    try:
        return CustomerResponse.model_validate(await use_cases.get(customer_id, tenant.tenant_id))
    except EntityNotFoundException as error:
        raise HTTPException(status_code=404, detail=error.message)


@router.patch("/{customer_id}", response_model=CustomerResponse, include_in_schema=False)
@router.patch("/{customer_id}/", response_model=CustomerResponse)
@inject
async def update_customer(
    customer_id: UUID,
    request: CustomerUpdateRequest,
    use_cases: FromDishka[CustomerUseCases],
    tenant: TenantContext = Depends(resolve_tenant_context),
) -> CustomerResponse:
    try:
        customer = await use_cases.update(
            customer_id, tenant.tenant_id, request.model_dump(exclude_unset=True),
        )
        return CustomerResponse.model_validate(customer)
    except EntityNotFoundException as error:
        raise HTTPException(status_code=404, detail=error.message)
    except BusinessRuleViolationException as error:
        raise HTTPException(status_code=400, detail=error.message)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="No se pudo guardar el cliente con las referencias indicadas.")

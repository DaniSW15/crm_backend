# Endpoints de clientes, oportunidades y sesión

Base: `/api/v1`. Las rutas de esta tabla aceptan directamente ambas variantes,
con y sin barra final. Las rutas existentes de `/deals` se conservan.

| Método | Ruta | Resultado |
| --- | --- | --- |
| POST | `/auth/login/` | `200`: token e información de sesión |
| POST | `/auth/logout/` | `204`: revoca el token presentado |
| GET | `/auth/me/` | `200`: usuario y organización actuales |
| GET | `/customers/` | `200`: arreglo de clientes del tenant |
| POST | `/customers/` | `201`: cliente creado |
| GET | `/customers/{id}/` | `200`: detalle del cliente |
| PATCH | `/customers/{id}/` | `200`: cliente actualizado |
| GET | `/opportunities/` | `200`: arreglo de oportunidades |
| POST | `/opportunities/` | `201`: oportunidad creada |
| GET | `/analytics/summary/` | `200`: indicadores del tenant |

Salvo el login, requieren `Authorization: Bearer <token>`. El registro público
existente sigue disponible en `POST /auth/register-tenant`.

## Sesión

El login recibe `{"email":"usuario@example.test","password":"<contraseña>"}`
y mantiene la respuesta existente (`access_token`, `token_type`, `user_id`,
`tenant_id`, `email`, `full_name`, `role`).

El logout no recibe body. Guarda únicamente la huella SHA256 del token con su
expiración en PostgreSQL. Desde la siguiente petición, ese token recibe `401` en
todas las rutas protegidas, incluso en otra instancia de la API. Las demás sesiones
del usuario siguen vigentes. Un segundo logout con el token ya revocado devuelve
`401`; solicitudes simultáneas no generan revocaciones duplicadas.

Los tokens nuevos tienen un identificador aleatorio de sesión. Se siguen aceptando
tokens anteriores sin ese identificador si su firma y expiración son válidas.
Se rechazan tokens sin expiración, vencidos o con algoritmo incompatible.

La consulta de revocaciones usa una sesión de BD independiente de la transacción
del negocio. Requiere la tabla `identity_revoked_tokens`; si la BD no está disponible,
la petición falla y no se omite la comprobación. Las filas vencidas pueden depurarse
por `expires_at` como mantenimiento, una vez expirados los tokens correspondientes.

## Clientes

`customers` representa las empresas cliente del CRM: reutiliza `crm_accounts`,
sin duplicar datos ni confundir clientes comerciales con usuarios de rol `CLIENTE`.

Creación mínima:

```json
{"name": "Acme"}
```

Campos opcionales: `industry`, `website`, `phone`, `annual_revenue`, `owner_id`,
`custom_fields`. Los ingresos son decimales no negativos con hasta dos decimales;
se devuelven como cadena decimal. El propietario debe existir en la organización
y no estar borrado. El cliente no puede asignar `tenant_id` ni `id`.

`GET /customers/` admite `limit` (1–100, por defecto 50) y `offset` (desde 0).
Devuelve un arreglo JSON; excluye clientes borrados y de otras organizaciones.

`PATCH` actualiza únicamente los campos enviados. Permite `null` para limpiar
campos opcionales, incluido `owner_id`; `name` y `custom_fields` no aceptan `null`.
Un cliente ajeno, borrado o inexistente produce el mismo `404`. Un propietario
ajeno, borrado o inexistente produce el mismo `400`. Los datos mal formados
producen `422`. Las escrituras son transaccionales.

## Oportunidades

`/opportunities/` reutiliza exactamente los casos de uso y esquemas de `/deals`.
La creación requiere `title`, `amount`, `pipeline_id`, `stage_id`, `owner_id`;
acepta los campos opcionales existentes. Para asociar un cliente se utiliza
`account_id` con el UUID retornado por `/customers/`.

El listado conserva filtros `pipeline_id`, `stage_id`, `status`, `limit`, `offset`
y devuelve un arreglo. Los montos de respuesta se serializan como cadenas decimales.
Las operaciones existentes de edición, movimiento y borrado siguen en `/deals`.

Una organización recién registrada todavía necesita un pipeline y etapas
provisionados; esta entrega no agrega administración de pipelines.

## Indicadores

El resumen considera exclusivamente cuentas y oportunidades no borradas del tenant:

```json
{
  "total_customers": 3,
  "total_opportunities": 2,
  "open_opportunities": 1,
  "won_opportunities": 1,
  "lost_opportunities": 0,
  "amounts_by_currency": [
    {
      "currency": "USD",
      "open_amount": "100.00",
      "won_amount": "200.00",
      "lost_amount": "0.00",
      "total_amount": "300.00"
    }
  ]
}
```

Los importes se agrupan por moneda, sin conversión ni suma entre monedas distintas.
Sin datos devuelve contadores en cero y `amounts_by_currency: []`. Las métricas
de estado usan `deal.status`: mover a una etapa marcada como ganada o perdida no
cambia automáticamente ese estado bajo las reglas actuales del backend.

## Migraciones y ejecución

Para una **base vacía** con `DATABASE_URL` configurada:

```sh
DEBUG=false .venv/bin/alembic upgrade head
DEBUG=false .venv/bin/uvicorn src.main:app --reload
```

La primera revisión crea el esquema previo del CRM y la segunda añade la tabla de
revocaciones. Ambas tienen `downgrade`. En una base existente creada mediante
`create_all`, primero hay que verificar que el esquema coincida con la revisión
inicial antes de marcarla con `alembic stamp 0001_initial_schema` y ejecutar
`alembic upgrade head`. No se debe aplicar la creación inicial sobre tablas existentes
ni marcarlas como migradas sin comparar su esquema. El arranque local con `DEBUG=true`
conserva la creación automática de tablas, incluida la tabla de revocaciones.

## Pruebas

Suite local, sin servicios externos:

```sh
DEBUG=false .venv/bin/python -B -m unittest discover -s tests -v
```

Para incluir flujos HTTP completos y revocaciones concurrentes con PostgreSQL,
define `TEST_DATABASE_URL` hacia una **base de pruebas** y ejecuta el mismo comando.
Cada prueba crea y elimina su propio esquema temporal; necesita permiso para ello.
No modifica las tablas de `public`. Las migraciones también deben comprobarse en
una base de pruebas vacía con `upgrade head`, `downgrade base`, `upgrade head`
y `alembic check`.

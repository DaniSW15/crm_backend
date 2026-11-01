# CRM Backend

Backend de FastAPI organizado como monolito modular. `identity` gestiona organizaciones
y usuarios; `crm` gestiona oportunidades y embudos de ventas.

La API también expone clientes (`/api/v1/customers/`), oportunidades mediante la
ruta compatible `/api/v1/opportunities/`, indicadores (`/api/v1/analytics/summary/`)
y cierre de sesión con revocación persistente (`/api/v1/auth/logout/`). Los contratos,
ejemplos y pasos de migración están en [la guía de endpoints](docs/api-endpoints.md).

## Organización

Cada módulo mantiene estas responsabilidades:

- `domain`: entidades y reglas del negocio, independientes de frameworks y base de datos.
- `application`: casos de uso, DTO y contratos de persistencia y servicios externos.
- `infrastructure`: modelos SQLAlchemy, repositorios y adaptadores de seguridad.
- `presentation`: rutas HTTP y esquemas de entrada y salida.

`core` configura la aplicación, la autenticación HTTP, la conexión a la base de datos
y el contenedor Dishka. `shared` contiene contratos e infraestructura reutilizables.

Los casos de uso dependen de contratos. Dishka conecta esos contratos con sus
implementaciones y proporciona una sesión de base de datos por petición.

## Transacciones

Cada caso de uso que escribe datos ejecuta toda la operación dentro de `UnitOfWork`.
Los repositorios usan `flush()` para enviar cambios a la base de datos sin confirmarlos.
La unidad de trabajo hace commit al terminar y rollback si hay un error.

La oportunidad y su historial se guardan juntos. Lo mismo ocurre al registrar una
organización con su primer administrador. Los nuevos casos de uso de escritura deben
seguir este patrón; los repositorios no deben llamar a `commit()`.

Al crear una oportunidad o cambiar su etapa, se busca el pipeline en el tenant actual
y se comprueba que esté activo y contenga la etapa solicitada.

Al crear o editar una oportunidad, el propietario y las referencias opcionales a
cuenta y contacto deben existir en el tenant actual y no estar borrados. La validación
ocurre dentro de la transacción. Una referencia inexistente, ajena o borrada devuelve
el mismo error `400`, sin revelar si existe en otra organización ni guardar cambios
parciales. Una oportunidad antigua con referencias inválidas también rechaza ediciones
hasta corregirlas.

Mover una oportunidad abierta a su etapa actual devuelve la oportunidad sin volver
a guardarla ni añadir historial. Reintentar un movimiento ya aplicado conserva un
solo registro de transición. Se mantienen las validaciones del tenant, pipeline y
estado: los tratos cerrados siguen rechazando movimientos, incluso a su etapa actual.

Identity recibe `PasswordHasher` y `TokenService` por inyección. Sus casos de uso
no necesitan conocer los algoritmos de contraseñas ni la implementación de JWT.

## Autenticación y desarrollo

Con `DEBUG=false`, las rutas protegidas requieren un Bearer JWT válido.
`X-Tenant-ID` y `X-User-ID` no autentican peticiones en ese modo.

Con `DEBUG=true`, se mantienen los headers y valores demo para desarrollo local.
Este modo permite el acceso demo como administrador y no debe usarse en producción.
Un Bearer inválido se rechaza incluso en desarrollo.

Las peticiones con Bearer también comprueban que el token no haya sido revocado.
En producción se debe aplicar la migración de `identity_revoked_tokens` antes de
arrancar la API. Logout invalida únicamente la sesión presentada; otros tokens
del mismo usuario siguen vigentes.

El arranque en desarrollo conserva la creación de tablas y datos demo. También se
puede ejecutar el seed explícitamente desde la raíz del proyecto:

```sh
DEBUG=true .venv/bin/python -m scripts.seed_demo
```

Este comando crea las tablas que falten e inserta los datos demo. El seed vive en
`scripts/seed_demo.py`; los cambios de esquema de producción se gestionan con Alembic.

## Pruebas

Con las dependencias del proyecto instaladas en `.venv`:

```sh
DEBUG=false .venv/bin/python -B -m unittest discover -s tests -v
```

Las pruebas cubren autenticación, permisos, aislamiento de etapas, inyección de
dependencias y persistencia atómica ante errores y cancelaciones. Usan ASGI directamente
y repositorios reales sobre SQLite con un adaptador async de pruebas. No requieren
servicios externos ni sustituyen una prueba de integración con PostgreSQL y asyncpg.

Las pruebas de `test_endpoints_postgres.py` sí ejecutan flujos HTTP con PostgreSQL
y asyncpg cuando se define `TEST_DATABASE_URL` hacia una base de pruebas. Crean un
esquema temporal independiente por prueba y cubren clientes, aislamiento, aliases de
oportunidades, indicadores y revocación de sesiones, incluidas escrituras concurrentes.

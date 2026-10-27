# CRM Backend

Backend de FastAPI organizado como monolito modular. `identity` gestiona organizaciones
y usuarios; `crm` gestiona oportunidades y embudos de ventas.

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

Identity recibe `PasswordHasher` y `TokenService` por inyección. Sus casos de uso
no necesitan conocer los algoritmos de contraseñas ni la implementación de JWT.

## Autenticación y desarrollo

Con `DEBUG=false`, las rutas protegidas requieren un Bearer JWT válido.
`X-Tenant-ID` y `X-User-ID` no autentican peticiones en ese modo.

Con `DEBUG=true`, se mantienen los headers y valores demo para desarrollo local.
Este modo permite el acceso demo como administrador y no debe usarse en producción.
Un Bearer inválido se rechaza incluso en desarrollo.

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

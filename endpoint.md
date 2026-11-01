# Documentación de Endpoints - CRM Backend API

Guía de referencia rápida de todos los endpoints disponibles en el backend de FastAPI para consumir desde **Angular**, **React** o probar en **Swagger / Postman**.

---

## 📌 Información General

- **Base URL:** `http://localhost:8000/api/v1`
- **Documentación Interactiva (Swagger):** `http://localhost:8000/docs`
- **Health Check:** `GET http://localhost:8000/health`
- **Formato de Peticiones:** `application/json`
- **Autenticación:** `Authorization: Bearer <TU_TOKEN_JWT>`

---

## 👥 Usuarios de Prueba Precargados

Todos los usuarios tienen la contraseña: **`admin123`**

| Email | Contraseña | Rol | Permisos |
| :--- | :--- | :---: | :--- |
| `admin@democrm.com` | `admin123` | **`ADMIN`** | Control total (GET, POST, PUT, DELETE) |
| `dev@democrm.com` | `admin123` | **`DEV`** | Control total de desarrollo (GET, POST, PUT, DELETE) |
| `cliente@democrm.com` | `admin123` | **`CLIENTE`** | Consulta y edición (GET, POST, PUT). **NO puede DELETE** |

---

## 🛡️ Matriz de Permisos por Rol

| Endpoint | Método | `ADMIN` | `DEV` | `CLIENTE` |
| :--- | :---: | :---: | :---: | :---: |
| `/auth/register-tenant` | `POST` | Público | Público | Público |
| `/auth/login` | `POST` | Público | Público | Público |
| `/auth/me` | `GET` | ✅ | ✅ | ✅ |
| `/pipelines` | `GET` | ✅ | ✅ | ✅ |
| `/deals` | `GET` | ✅ | ✅ | ✅ |
| `/deals` | `POST` | ✅ | ✅ | ✅ |
| `/deals/{id}` | `PUT` | ✅ | ✅ | ✅ |
| `/deals/{id}/move-stage`| `POST` | ✅ | ✅ | ✅ |
| `/deals/{id}` | `DELETE`| ✅ | ✅ | ❌ **403 Forbidden** |

---

## 1. Módulo de Autenticación (`/auth`)

### 1.1 Iniciar Sesión (Login)
Obtiene el token JWT necesario para todas las demás peticiones.

- **Método:** `POST`
- **URL:** `/api/v1/auth/login`
- **Acceso:** Público (sin token)

#### Request Body:
```json
{
  "email": "admin@democrm.com",
  "password": "admin123"
}
```

#### Response Exitosa (`200 OK`):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "00000000-0000-0000-0000-000000000002",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "email": "admin@democrm.com",
  "full_name": "Admin Demo",
  "role": "ADMIN"
}
```

---

### 1.2 Registrar Nueva Organización y Admin
Crea una empresa y su primer usuario administrador.

- **Método:** `POST`
- **URL:** `/api/v1/auth/register-tenant`
- **Acceso:** Público (sin token)

#### Request Body:
```json
{
  "company_name": "Mi Empresa S.A.",
  "slug": "mi-empresa",
  "admin_full_name": "Juan Pérez",
  "admin_email": "juan@miempresa.com",
  "admin_password": "PasswordSeguro123!"
}
```

#### Response Exitosa (`201 Created`):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "uuid-generado",
  "tenant_id": "uuid-generado",
  "email": "juan@miempresa.com",
  "full_name": "Juan Pérez",
  "role": "ADMIN"
}
```

---

### 1.3 Obtener Perfil del Usuario Actual
Devuelve la información del usuario autenticado y su empresa.

- **Método:** `GET`
- **URL:** `/api/v1/auth/me`
- **Headers Requeridos:** `Authorization: Bearer <TOKEN>`
- **Acceso:** Cualquier usuario autenticado (`ADMIN`, `DEV`, `CLIENTE`)

#### Response Exitosa (`200 OK`):
```json
{
  "id": "00000000-0000-0000-0000-000000000002",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "email": "admin@democrm.com",
  "full_name": "Admin Demo",
  "role": "ADMIN",
  "is_active": true,
  "tenant": {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "Organización Demo",
    "slug": "demo-corp",
    "plan": "ENTERPRISE",
    "is_active": true
  }
}
```

---

## 2. Módulo de Embudos de Venta (`/pipelines`)

### 2.1 Listar Embudos y Etapas (Kanban)
Obtiene los embudos de venta con todas sus etapas ordenadas. Ideal para pintar las columnas del tablero Kanban.

- **Método:** `GET`
- **URL:** `/api/v1/pipelines`
- **Headers Requeridos:** `Authorization: Bearer <TOKEN>`
- **Acceso:** Cualquier usuario autenticado

#### Response Exitosa (`200 OK`):
```json
[
  {
    "id": "a0000000-0000-0000-0000-000000000001",
    "name": "Embudo Principal de Ventas",
    "is_default": true,
    "is_active": true,
    "stages": [
      {
        "id": "b0000000-0000-0000-0000-000000000001",
        "pipeline_id": "a0000000-0000-0000-0000-000000000001",
        "name": "Prospección",
        "order": 1,
        "win_probability": 20.0,
        "days_until_stale": 14,
        "is_won_stage": false,
        "is_lost_stage": false
      },
      {
        "id": "b0000000-0000-0000-0000-000000000002",
        "pipeline_id": "a0000000-0000-0000-0000-000000000001",
        "name": "Demostración y Propuesta",
        "order": 2,
        "win_probability": 60.0,
        "days_until_stale": 14,
        "is_won_stage": false,
        "is_lost_stage": false
      },
      {
        "id": "b0000000-0000-0000-0000-000000000003",
        "pipeline_id": "a0000000-0000-0000-0000-000000000001",
        "name": "Cerrado Ganado",
        "order": 3,
        "win_probability": 100.0,
        "days_until_stale": 14,
        "is_won_stage": true,
        "is_lost_stage": false
      }
    ]
  }
]
```

---

## 3. Módulo de Oportunidades (`/deals`)

### 3.1 Listar Oportunidades
Lista oportunidades comerciales con filtros opcionales.

- **Método:** `GET`
- **URL:** `/api/v1/deals`
- **Headers Requeridos:** `Authorization: Bearer <TOKEN>`
- **Query Params (Opcionales):**
  - `pipeline_id` (UUID): Filtrar por embudo
  - `stage_id` (UUID): Filtrar por etapa
  - `status` (string): `OPEN`, `WON` o `LOST`
  - `limit` (int, default: 50)
  - `offset` (int, default: 0)

#### Response Exitosa (`200 OK`):
```json
[
  {
    "id": "07fe4911-e919-47c4-abde-7ec92ed831c4",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "title": "Licencia Anual Acme Corp",
    "amount": "15000.00",
    "currency": "USD",
    "pipeline_id": "a0000000-0000-0000-0000-000000000001",
    "stage_id": "b0000000-0000-0000-0000-000000000001",
    "owner_id": "c0000000-0000-0000-0000-000000000001",
    "status": "OPEN",
    "account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "contact_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "expected_close_date": "2026-12-31",
    "actual_close_date": null,
    "lost_reason": null,
    "custom_fields": {}
  }
]
```

---

### 3.2 Crear Oportunidad
Crea un nuevo trato comercial y lo asigna a la primera etapa.

- **Método:** `POST`
- **URL:** `/api/v1/deals`
- **Headers Requeridos:** `Authorization: Bearer <TOKEN>`

#### Request Body:
```json
{
  "title": "Implementación CRM Enterprise",
  "amount": 25000.00,
  "currency": "USD",
  "pipeline_id": "a0000000-0000-0000-0000-000000000001",
  "stage_id": "b0000000-0000-0000-0000-000000000001",
  "owner_id": "c0000000-0000-0000-0000-000000000001",
  "account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "contact_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "expected_close_date": "2026-12-31",
  "custom_fields": {}
}
```
*(Los campos `account_id` y `contact_id` pueden ser `null` si aún no hay empresa o contacto asociado)*.

#### Response Exitosa (`201 Created`):
```json
{
  "id": "uuid-del-nuevo-trato",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "title": "Implementación CRM Enterprise",
  "amount": "25000.00",
  "currency": "USD",
  "pipeline_id": "a0000000-0000-0000-0000-000000000001",
  "stage_id": "b0000000-0000-0000-0000-000000000001",
  "owner_id": "c0000000-0000-0000-0000-000000000001",
  "status": "OPEN",
  "account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "contact_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "expected_close_date": "2026-12-31",
  "actual_close_date": null,
  "lost_reason": null,
  "custom_fields": {}
}
```

---

### 3.3 Editar Oportunidad (Actualizar Datos)
Modifica los datos de una oportunidad existente.

- **Método:** `PUT`
- **URL:** `/api/v1/deals/{deal_id}`
- **Headers Requeridos:** `Authorization: Bearer <TOKEN>`
- **Acceso:** `ADMIN`, `DEV`, `CLIENTE`

#### Request Body (solo envías lo que deseas cambiar):
```json
{
  "title": "Implementación CRM Enterprise (Renegociado)",
  "amount": 32000.00,
  "currency": "USD",
  "expected_close_date": "2027-01-15"
}
```

#### Response Exitosa (`200 OK`):
Retorna el objeto `Deal` actualizado con los nuevos valores.

---

### 3.4 Mover Etapa de Oportunidad (Kanban Move)
Mueve el trato a una nueva columna y guarda el registro histórico para analítica.

- **Método:** `POST`
- **URL:** `/api/v1/deals/{deal_id}/move-stage`
- **Headers Requeridos:** `Authorization: Bearer <TOKEN>`
- **Acceso:** `ADMIN`, `DEV`, `CLIENTE`

#### Request Body:
```json
{
  "new_stage_id": "b0000000-0000-0000-0000-000000000002"
}
```

#### Response Exitosa (`200 OK`):
Retorna el objeto `Deal` con el nuevo `stage_id`.

---

### 3.5 Eliminar Oportunidad (Borrado Lógico)
Elimina una oportunidad del sistema.

- **Método:** `DELETE`
- **URL:** `/api/v1/deals/{deal_id}`
- **Headers Requeridos:** `Authorization: Bearer <TOKEN>`
- **Acceso:** 🔒 **SOLO `ADMIN` Y `DEV`**

#### Comportamiento por Rol:
- **Si eres `ADMIN` o `DEV`:**
  - Status: `204 No Content` (éxito sin cuerpo).
- **Si eres `CLIENTE`:**
  - Status: `403 Forbidden`
  ```json
  {
    "detail": "Acceso denegado: tu rol 'CLIENTE' no tiene permiso para esta operación. Roles requeridos: ADMIN, DEV."
  }
  ```

---

## 4. Códigos de Estado HTTP (Status Codes)

| Código | Significado | ¿Cuándo ocurre? |
| :---: | :--- | :--- |
| **`200 OK`** | Petición exitosa | Al consultar (`GET`) o editar (`PUT`). |
| **`201 Created`** | Registro creado | Al registrarse o crear una oportunidad (`POST`). |
| **`204 No Content`** | Eliminado con éxito | Al borrar (`DELETE`). |
| **`400 Bad Request`** | Error en los datos | Formato JSON incorrecto o regla de negocio rota. |
| **`401 Unauthorized`** | No autenticado | Token ausente, vencido o contraseña incorrecta. |
| **`403 Forbidden`** | Sin permiso de rol | Un `CLIENTE` intentando hacer `DELETE`. |
| **`404 Not Found`** | No encontrado | El ID de la oportunidad o usuario no existe. |


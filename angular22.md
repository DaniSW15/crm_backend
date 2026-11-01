# Guía de Arquitectura y Conexión Frontend en Angular (18 / 19+)

Guía técnica, moderna y completa para estructurar una aplicación frontend en **Angular moderno** (Standalone Components, Signals, inyección funcional con `inject()`, control flow `@if` / `@for` / `@empty`, interceptores funcionales y consumo de la API de este backend FastAPI).

---

## 1. Estructura de Carpetas Recomendada (Modular / Vertical Slices)

```text
src/
├── app/
│   ├── core/                           # Singletons y configuración global
│   │   ├── auth/                       # Lógica de sesión y seguridad
│   │   │   ├── auth.service.ts         # Servicio con Signals (currentUser, isAuthenticated)
│   │   │   └── auth.guard.ts           # Functional Guard (canActivateFn)
│   │   ├── interceptors/               # Interceptores HTTP funcionales
│   │   │   ├── auth.interceptor.ts     # Inyección automática de Bearer Token JWT
│   │   │   └── error.interceptor.ts    # Captura global de errores (401, 403, 500)
│   │   ├── models/                     # Interfaces y tipos globales (User, Tenant, ApiError)
│   │   └── services/                   # Notificaciones (toast), Storage
│   │
│   ├── layout/                         # Cascarón visual de la aplicación
│   │   ├── components/                 # Navbar, Sidebar de navegación, UserMenu
│   │   └── main-layout.component.ts    # Contenedor principal con <router-outlet />
│   │
│   ├── shared/                         # Componentes y utilidades reutilizables
│   │   ├── components/                 # Botones, Modales, Tablas, LoadingSpinner
│   │   ├── pipes/                      # CurrencyPipe personalizado, DateAgoPipe
│   │   └── directives/                 # ClickOutsideDirective, HasRoleDirective
│   │
│   ├── features/                       # Módulos por dominio de negocio (Vertical Slices)
│   │   ├── auth/                       # Login y Registro de Organizaciones
│   │   │   ├── pages/
│   │   │   │   ├── login/
│   │   │   │   └── register/
│   │   │   └── auth.routes.ts
│   │   │
│   │   └── deals/                      # Oportunidades y Embudo de Ventas (CRM)
│   │       ├── models/                 # Deal, DealCreateRequest, MoveDealStageRequest
│   │       ├── services/               # DealService (CRUD y cambio de etapa)
│   │       ├── pages/
│   │       │   ├── deal-list/          # Vista de lista / Kanban de ventas
│   │       │   └── deal-create/        # Formulario reactivo para crear tratos
│   │       └── deals.routes.ts         # Rutas con Lazy Loading
│   │
│   ├── app.config.ts                   # Proveedores raíz (provideHttpClient con withFetch)
│   ├── app.routes.ts                   # Enrutamiento raíz con carga diferida
│   └── app.component.ts                # Componente raíz
│
└── environments/                       # Variables de configuración por entorno
    ├── environment.ts                  # Producción
    └── environment.development.ts      # Desarrollo local
```

---

## 2. Responsabilidad de Cada Capa

| Capa | Propósito | Regla de Oro |
| :--- | :--- | :--- |
| **`core/`** | Autenticación, interceptores, guards y estado de sesión. | Se inicializa una sola vez. No debe importar nada de `features/`. |
| **`shared/`** | Componentes UI tontos (presentacionales), pipes y directivas. | Cero lógica de negocio de CRM o autenticación. |
| **`layout/`** | Estructura visual de la aplicación (Sidebar, Header con usuario activo). | Aloja el `<router-outlet />` principal del área privada. |
| **`features/`** | Pantallas y servicios específicos de cada área (`deals`, `contacts`, `auth`). | Totalmente modular e independiente. Se carga mediante *Lazy Loading*. |

---

## 3. Configuración Raíz y Variables de Entorno

### A. Variables de Entorno
📁 `src/environments/environment.development.ts`
```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1' // URL base del backend FastAPI
};
```

📁 `src/environments/environment.ts`
```typescript
export const environment = {
  production: true,
  apiUrl: 'https://api.tu-crm.com/api/v1'
};
```

### B. Configuración Global (`app.config.ts`)
Configuramos `provideHttpClient` con la API moderna `withFetch()` (optimización de red nativa) y los interceptores funcionales:

📁 `src/app/app.config.ts`
```typescript
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter, withComponentInputBinding, withViewTransitions } from '@angular/router';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(
      routes,
      withComponentInputBinding(), // Pasa params de URL directamente como inputs() al componente
      withViewTransitions()        // Transiciones visuales nativas entre páginas
    ),
    provideHttpClient(
      withFetch(),                 // Usa fetch() moderno en lugar de XMLHttpRequest
      withInterceptors([authInterceptor, errorInterceptor])
    )
  ]
};
```

---

## 4. Núcleo de Seguridad y Autenticación (`core/auth`)

### A. Modelos de Autenticación
📁 `src/app/core/models/auth.model.ts`
```typescript
export interface User {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: 'ADMIN' | 'SALES_MANAGER' | 'SALES_REP';
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface UserProfileResponse {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  tenant: {
    id: string;
    name: string;
    slug: string;
    plan: string;
    is_active: boolean;
  };
}
```

### B. Servicio de Autenticación con Signals
📁 `src/app/core/auth/auth.service.ts`
```typescript
import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthResponse, UserProfileResponse } from '../models/auth.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private readonly baseUrl = `${environment.apiUrl}/auth`;

  // Estado reactivo con Signals
  private currentUserSignal = signal<UserProfileResponse | null>(null);
  readonly currentUser = this.currentUserSignal.asReadonly();
  readonly isAuthenticated = computed(() => !!this.getToken());
  readonly userRole = computed(() => this.currentUserSignal()?.role ?? null);

  constructor() {
    if (this.getToken()) {
      this.loadProfile().subscribe({
        error: () => this.logout()
      });
    }
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  login(credentials: { email: string; password: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/login`, credentials).pipe(
      tap(res => {
        localStorage.setItem('access_token', res.access_token);
        this.loadProfile().subscribe();
      })
    );
  }

  loadProfile(): Observable<UserProfileResponse> {
    return this.http.get<UserProfileResponse>(`${this.baseUrl}/me`).pipe(
      tap(profile => this.currentUserSignal.set(profile))
    );
  }

  logout(): void {
    localStorage.removeItem('access_token');
    this.currentUserSignal.set(null);
    this.router.navigate(['/auth/login']);
  }
}
```

### C. Interceptor HTTP para JWT
Inyecta automáticamente el token en cada petición al backend y limpia la sesión si recibe un `401 Unauthorized`:

📁 `src/app/core/interceptors/auth.interceptor.ts`
```typescript
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { environment } from '../../../environments/environment';
import { AuthService } from '../auth/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.getToken();

  // Solo adjuntar token si la petición se dirige a nuestra API
  const isApiUrl = req.url.startsWith(environment.apiUrl);

  if (token && isApiUrl) {
    const authReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    return next(authReq);
  }

  return next(req);
};
```

📁 `src/app/core/interceptors/error.interceptor.ts`
```typescript
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../auth/auth.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !req.url.includes('/auth/login')) {
        authService.logout();
      }
      return throwError(() => error);
    })
  );
};
```

### D. Functional Auth Guard
Protege las rutas privadas impidiendo el acceso a usuarios no autenticados:

📁 `src/app/core/auth/auth.guard.ts`
```typescript
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }

  return router.createUrlTree(['/auth/login']);
};
```

---

## 5. Implementación de un Feature de Negocio: Oportunidades (`features/deals`)

### A. Modelos y DTOs de Oportunidades
📁 `src/app/features/deals/models/deal.model.ts`
```typescript
export type DealStatus = 'OPEN' | 'WON' | 'LOST';

export interface Deal {
  id: string;
  tenant_id: string;
  title: string;
  amount: number;
  currency: string;
  pipeline_id: string;
  stage_id: string;
  owner_id: string;
  status: DealStatus;
  account_id?: string | null;
  contact_id?: string | null;
  expected_close_date?: string | null;
  actual_close_date?: string | null;
  lost_reason?: string | null;
  custom_fields?: Record<string, any>;
}

export interface DealCreateRequest {
  title: string;
  amount: number;
  currency: string;
  pipeline_id: string;
  stage_id: string;
  owner_id: string;
  account_id?: string | null;
  contact_id?: string | null;
  expected_close_date?: string | null;
  custom_fields?: Record<string, any>;
}

export interface MoveDealStageRequest {
  new_stage_id: string;
}
```

### B. Servicio de Oportunidades (`DealService`)
📁 `src/app/features/deals/services/deal.service.ts`
```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Deal, DealCreateRequest, MoveDealStageRequest } from '../models/deal.model';

@Injectable({
  providedIn: 'root'
})
export class DealService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/deals`;

  // Listar oportunidades con filtros opcionales
  getDeals(filters?: { pipeline_id?: string; stage_id?: string; status?: string }): Observable<Deal[]> {
    let params = new HttpParams();
    if (filters?.pipeline_id) params = params.set('pipeline_id', filters.pipeline_id);
    if (filters?.stage_id) params = params.set('stage_id', filters.stage_id);
    if (filters?.status) params = params.set('status', filters.status);

    return this.http.get<Deal[]>(this.baseUrl, { params });
  }

  // Crear oportunidad
  createDeal(payload: DealCreateRequest): Observable<Deal> {
    return this.http.post<Deal>(this.baseUrl, payload);
  }

  // Actualizar oportunidad existente (PUT)
  updateDeal(dealId: string, payload: Partial<DealCreateRequest>): Observable<Deal> {
    return this.http.put<Deal>(`${this.baseUrl}/${dealId}`, payload);
  }

  // Cambiar etapa en el embudo comercial (Kanban move)
  moveStage(dealId: string, newStageId: string): Observable<Deal> {
    const payload: MoveDealStageRequest = { new_stage_id: newStageId };
    return this.http.post<Deal>(`${this.baseUrl}/${dealId}/move-stage`, payload);
  }

  // Eliminar oportunidad (Solo permitido para ADMIN y DEV)
  deleteDeal(dealId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${dealId}`);
  }

  // Obtener embudos de venta y etapas ordenadas (Kanban)
  getPipelines(): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiUrl}/pipelines`);
  }
}
```

### C. Componente con Signals y Control Flow (`@if`, `@for`, `@empty`)
📁 `src/app/features/deals/pages/deal-list/deal-list.component.ts`
```typescript
import { Component, OnInit, inject, signal } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { DealService } from '../../services/deal.service';
import { Deal } from '../../models/deal.model';

@Component({
  selector: 'app-deal-list',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, RouterLink],
  template: `
    <div class="page-container">
      <header class="page-header">
        <h1>Oportunidades Comerciales</h1>
        <a routerLink="new" class="btn btn-primary">+ Nueva Oportunidad</a>
      </header>

      <!-- Estado de carga -->
      @if (loading()) {
        <div class="loading-state">
          <p>Cargando oportunidades del CRM...</p>
        </div>
      }

      <!-- Alerta de error -->
      @if (errorMessage()) {
        <div class="alert alert-error">
          {{ errorMessage() }}
        </div>
      }

      <!-- Tabla de oportunidades -->
      @if (!loading()) {
        <div class="table-card">
          <table>
            <thead>
              <tr>
                <th>Título</th>
                <th>Monto</th>
                <th>Estado</th>
                <th>Cierre Estimado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              @for (deal of deals(); track deal.id) {
                <tr>
                  <td class="font-medium">{{ deal.title }}</td>
                  <td>{{ deal.amount | currency:deal.currency:'symbol':'1.2-2' }}</td>
                  <td>
                    <span class="badge" [class]="'badge-' + deal.status.toLowerCase()">
                      {{ deal.status }}
                    </span>
                  </td>
                  <td>{{ deal.expected_close_date ? (deal.expected_close_date | date:'dd/MM/yyyy') : 'N/A' }}</td>
                  <td>
                    <button class="btn btn-sm" (click)="onMoveToNextStage(deal)">Avanzar Etapa</button>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="5" class="empty-state">
                    No hay oportunidades comerciales registradas en este momento.
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `
})
export class DealListComponent implements OnInit {
  private dealService = inject(DealService);

  // Estados reactivos con Signals
  deals = signal<Deal[]>([]);
  loading = signal<boolean>(false);
  errorMessage = signal<string | null>(null);

  ngOnInit(): void {
    this.fetchDeals();
  }

  fetchDeals(): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    this.dealService.getDeals().subscribe({
      next: (data) => {
        this.deals.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMessage.set('No se pudieron obtener las oportunidades comerciales.');
        this.loading.set(false);
        console.error(err);
      }
    });
  }

  onMoveToNextStage(deal: Deal): void {
    // Ejemplo de avance a la siguiente etapa de demostración
    const demoStageId = 'b0000000-0000-0000-0000-000000000002';

    this.dealService.moveStage(deal.id, demoStageId).subscribe({
      next: (updatedDeal) => {
        // Actualización inmutable del Signal sin recargar la lista completa
        this.deals.update(currentList =>
          currentList.map(item => (item.id === updatedDeal.id ? updatedDeal : item))
        );
      },
      error: (err) => {
        alert(err.error?.detail || 'Error al mover la etapa de la oportunidad.');
      }
    });
  }
}
```

---

## 6. Configuración de Rutas con Lazy Loading (`app.routes.ts`)

📁 `src/app/features/deals/deals.routes.ts`
```typescript
import { Routes } from '@angular/router';

export const DEAL_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/deal-list/deal-list.component').then(m => m.DealListComponent)
  }
];
```

📁 `src/app/app.routes.ts`
```typescript
import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  // Rutas públicas (Autenticación)
  {
    path: 'auth',
    loadChildren: () =>
      import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES)
  },

  // Rutas protegidas (CRM)
  {
    path: '',
    canActivate: [authGuard],
    children: [
      {
        path: 'deals',
        loadChildren: () =>
          import('./features/deals/deals.routes').then(m => m.DEAL_ROUTES)
      },
      {
        path: '',
        redirectTo: 'deals',
        pathMatch: 'full'
      }
    ]
  },

  // Redirección para URLs desconocidas (404)
  {
    path: '**',
    redirectTo: 'deals'
  }
];
```

---

## 7. Buenas Prácticas Clave en Angular Moderno

1. **Standalone Components:** Olvídate de `NgModule`. Todo componente, directiva o pipe debe ser `standalone: true`.
2. **Inyección con `inject()`:** Usa la función `inject(Servicio)` en el constructor o inicializador de propiedad en lugar del constructor tradicional `constructor(private s: Servicio)`.
3. **Signals para Estado Local:** Usa `signal()` para valores reactivos y `computed()` para valores derivados. Disminuye la dependencia manual de RxJS `BehaviorSubject` dentro de tus componentes.
4. **Control Flow Nativo:**
   - Usa `@if (...) { ... } @else { ... }`.
   - Usa `@for (item of items(); track item.id) { ... } @empty { ... }` para iteraciones limpias con manejo de listas vacías sin directivas `*ngFor` ni `*ngIf`.
5. **Consumo HTTP Moderno:** Usa `provideHttpClient(withFetch(), withInterceptors([...]))` en `app.config.ts`.

---

## 8. Seguridad y Ocultamiento de Botones según el Rol (`ADMIN`, `DEV`, `CLIENTE`)

### A. Matriz de Permisos
| Rol | Significado | Ver (GET) | Crear (POST) | Editar (PUT) | Borrar (DELETE) |
|---|---|:---:|:---:|:---:|:---:|
| **`ADMIN`** | Jefe / Director | ✅ | ✅ | ✅ | ✅ |
| **`DEV`** | Desarrollador | ✅ | ✅ | ✅ | ✅ |
| **`CLIENTE`** | Usuario normal | ✅ | ✅ | ✅ | ❌ **(Oculto y Bloqueado)** |

### B. En el Componente Angular (TypeScript)
Usa un `computed` derivado del `authService.userRole`:

```typescript
export class DealListComponent {
  authService = inject(AuthService);
  dealService = inject(DealService);

  // Solo ADMIN y DEV tienen permiso para borrar
  readonly canDelete = computed(() => {
    const role = this.authService.userRole();
    return role === 'ADMIN' || role === 'DEV';
  });

  onDelete(dealId: string): void {
    if (!this.canDelete()) return;
    if (!confirm('¿Seguro que deseas eliminar este registro?')) return;

    this.dealService.deleteDeal(dealId).subscribe({
      next: () => {
        // Remover de la lista
        this.deals.update(list => list.filter(d => d.id !== dealId));
      },
      error: (err) => {
        alert(err.error?.detail || 'Error al eliminar');
      }
    });
  }
}
```

### C. En la Plantilla HTML (Angular)
El botón **Eliminar** se oculta automáticamente para el rol `CLIENTE`:

```html
@for (deal of deals(); track deal.id) {
  <tr>
    <td>{{ deal.title }}</td>
    <td>{{ deal.amount | currency }}</td>
    <td>
      <!-- Botón visible para todos -->
      <button class="btn btn-sm" (click)="onView(deal.id)">Ver</button>

      <!-- Botón ELIMINAR: Oculto para CLIENTE, visible para ADMIN y DEV -->
      @if (canDelete()) {
        <button class="btn btn-sm btn-danger" (click)="onDelete(deal.id)">
          🗑️ Eliminar
        </button>
      }
    </td>
  </tr>
}
```

> 🛡️ **Seguridad Garantizada:** Si un usuario con rol `CLIENTE` intenta llamar a `DELETE /api/v1/deals/{id}` directamente por consola o Postman, el backend FastAPI responderá automáticamente con **`403 Forbidden`**.

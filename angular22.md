# Guía Rápida de Estructura de Proyecto en Angular

Guía práctica y concisa para organizar una aplicación moderna en Angular (Standalone Components, Signals y arquitectura modular por características).

---

## 1. Estructura de Carpetas Recomendada

```text
src/
├── app/
│   ├── core/                      # Singleton / Configuración global (se carga una sola vez)
│   │   ├── auth/                  # Guards, interceptores de token, auth.service
│   │   ├── interceptors/          # ErrorHandler, loading, logging
│   │   ├── services/              # Notificaciones, storage, API cliente base
│   │   └── models/                # Interfaces/tipos globales (User, Session, ApiResponse)
│   │
│   ├── shared/                    # Reutilizable en cualquier parte de la app
│   │   ├── components/            # UI components tontos/presentacionales (botones, modales, tablas)
│   │   ├── directives/            # Directivas de utilidad (autofocus, click-outside)
│   │   ├── pipes/                 # Pipes comunes (date-format, currency, etc.)
│   │   └── ui/                    # Componentes base de diseño / design system
│   │
│   ├── layout/                    # Estructura del cascarón visual
│   │   ├── components/            # Header, Sidebar, Footer, Breadcrumbs
│   │   └── main-layout/           # Layout contenedor con <router-outlet />
│   │
│   ├── features/                  # Módulos por dominio de negocio (Vertical Slices)
│   │   └── [nombre-feature]/      # Ej: customers, dashboard, invoices
│   │       ├── components/        # Componentes específicos de este feature
│   │       ├── pages/             # Vistas conectadas a rutas (Smart Components)
│   │       ├── services/          # Llamadas a API y estado local del feature
│   │       ├── models/            # Interfaces exclusivas del feature
│   │       └── [feature].routes.ts# Rutas con lazy loading
│   │
│   ├── app.config.ts              # Proveedores globales (provideRouter, provideHttpClient, etc.)
│   ├── app.routes.ts              # Configuración de rutas raíz
│   └── app.component.ts           # Componente raíz con el router-outlet principal
└── environments/                  # Variables de entorno (API URL, keys)
    ├── environment.ts
    └── environment.development.ts
```

---

## 2. Responsabilidad de Cada Capa

| Capa | Propósito | Regla de Oro |
| :--- | :--- | :--- |
| **`core/`** | Infraestructura y servicios únicos de la app. | No debe importar nada de `features/` ni de `shared/`. |
| **`shared/`** | Componentes reutilizables, directivas y pipes puros. | No debe contener lógica de negocio específica de un dominio. |
| **`layout/`** | Estructura visual de navegación (shell). | Contiene el menú, barra superior y define el layout principal. |
| **`features/`** | Dominio y lógica de negocio específica. | Cada feature debe ser lo más autosuficiente e independiente posible. |

---

## 3. Patrones y Buenas Prácticas Modernas

### Standalone por Defecto
Usa componentes Standalone en todo el proyecto:
```typescript
@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule, UserCardComponent],
  templateUrl: './user-list.component.html'
})
export class UserListComponent {}
```

### Inyección con `inject()`
Prefiere la función `inject()` sobre la inyección en constructor:
```typescript
export class CustomerService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
}
```

### Reactividad con Signals
Usa Signals para el manejo de estado local y síncrono:
```typescript
export class CounterComponent {
  count = signal(0);
  double = computed(() => this.count() * 2);

  increment() {
    this.count.update(v => v + 1);
  }
}
```

### Carga Perezosa (Lazy Loading) en Rutas
Configura rutas hijas cargadas bajo demanda en `app.routes.ts`:
```typescript
export const routes: Routes = [
  {
    path: '',
    component: MainLayoutComponent,
    children: [
      {
        path: 'customers',
        loadChildren: () => import('./features/customers/customers.routes').then(m => m.CUSTOMER_ROUTES)
      }
    ]
  },
  {
    path: 'login',
    loadComponent: () => import('./features/auth/pages/login/login.component').then(m => m.LoginComponent)
  }
];
```

---

## 4. Convenciones de Nombres

- **Componentes:** `[nombre].component.ts`
- **Páginas / Vistas:** `[nombre].page.ts` o dentro de carpeta `pages/`
- **Servicios:** `[nombre].service.ts`
- **Modelos / Tipos:** `[nombre].model.ts`
- **Rutas:** `[nombre].routes.ts`
- **Interceptores:** `[nombre].interceptor.ts`
- **Guards:** `[nombre].guard.ts`


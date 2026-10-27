from contextlib import asynccontextmanager
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.di import create_container

settings = get_settings()


from src.core.database import async_session_factory, engine
from scripts.seed_demo import seed_initial_data
from src.shared.infrastructure.base_model import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # En desarrollo (DEBUG=True), inicializar automáticamente tablas y datos demo si PostgreSQL está listo
    if settings.DEBUG:
        db_target = str(settings.DATABASE_URL).split("@")[-1]
        print(f"🔍 [Database]: Intentando conectar a: {db_target}")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with async_session_factory() as session:
                await seed_initial_data(session)
            print("✅ [Database]: Tablas y datos demo inicializados correctamente.")
        except Exception as e:
            print(f"⚠️ [Database Setup]: No se pudo conectar a la base de datos PostgreSQL: {e}")
            print("👉 Si no tienes PostgreSQL corriendo, ejecuta: docker compose up -d")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else "/docs",  # Configurable
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Integrar el contenedor de inversión de dependencias Dishka
container = create_container()
setup_dishka(container, app)


from src.modules.crm.presentation.routes.deals import router as deals_router
from src.modules.crm.presentation.routes.pipelines import router as pipelines_router
from src.modules.identity.presentation.routes import router as auth_router

# Registrar routers de módulos
app.include_router(auth_router, prefix="/api/v1")
app.include_router(pipelines_router, prefix="/api/v1")
app.include_router(deals_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


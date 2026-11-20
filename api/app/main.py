from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api import api_router
from app.config import settings, setup_app_logging

setup_app_logging(config=settings)

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

root_router = APIRouter()


@root_router.get("/")
def index(request: Request) -> Any:
    body = ("<html><body style='padding: 10px; font-family: Arial'>"
            "<h1>UCI Analytics API</h1>"
            "<p>Riesgo de estancia &ge; 7 días y de muerte en UCI oncológica.</p>"
            "<div>Documentación: <a href='/docs'>/docs</a></div>"
            "</body></html>")
    return HTMLResponse(content=body)


app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(root_router)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=settings.BACKEND_CORS_ORIGINS,
                       allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

if __name__ == "__main__":  # solo para pruebas locales
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")

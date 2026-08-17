from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.endpoints import auth, exams, materials, student, admin, questions, topics, analytics, history, flashcards, ai_studio

from fastapi.middleware.cors import CORSMiddleware
import app.models  # Ensure all models are registered in SQLAlchemy
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.correlation import CorrelationMiddleware, REQUEST_ID_HEADER
from app.core.error_handlers import install_error_handlers

app = FastAPI(title="AI Quiz System")
app.state.limiter = limiter
install_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)
app.add_middleware(CorrelationMiddleware)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(topics.router, prefix="/topics", tags=["topics"])
app.include_router(exams.router, prefix="/exams", tags=["exams"])
app.include_router(materials.router, prefix="/materials", tags=["materials"])
app.include_router(student.router, prefix="/student", tags=["student"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(questions.router, prefix="/questions", tags=["questions"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(history.router, prefix="/history", tags=["history"])
app.include_router(flashcards.router, prefix="/flashcards", tags=["flashcards"])
app.include_router(ai_studio.router, prefix="/ai", tags=["ai"])

from app.core.file_storage import material_file_storage
material_file_storage.ensure_root()
app.mount(
    "/uploads/avatars",
    StaticFiles(directory="uploads/avatars", check_dir=False),
    name="avatars",
)

from fastapi_pagination import add_pagination

add_pagination(app)

@app.get("/")
def read_root():
    return {"message": "Server and database is running"}

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.domain.agent import connect_db, close_db
from src.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Opens the Neon connection pool when the server starts
    connect_db()
    yield
    # Safely closes the connection pool when the server shuts down
    close_db()

app = FastAPI(title="Persistent LangGraph Backend", lifespan=lifespan)

# CORS middleware so your Streamlit frontend can communicate with FastAPI smoothly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register your API routes
app.include_router(router)

@app.get("/health")
def health():
    """Health check endpoint used by Render/Docker to verify the container is running."""
    return {"status": "ok"}
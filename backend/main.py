import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

from auth import login_and_save_cookies, cookies_exist
from scraper import scrape_profile

load_dotenv()

app = FastAPI(title="Instagram Public Scraper", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ThreadPoolExecutor para correr código síncrono de Playwright sin bloquear
executor = ThreadPoolExecutor(max_workers=2)

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


class ScrapeRequest(BaseModel):
    username: str


@app.get("/")
async def root():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Instagram Scraper API"}


@app.post("/auth")
async def authenticate():
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, login_and_save_cookies, "", "")
        return {"success": True, "message": "Autenticación exitosa. Cookies guardadas.", "cookies_saved": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de autenticación: {str(e)}")


@app.get("/auth/status")
async def auth_status():
    return {
        "authenticated": cookies_exist(),
        "message": "Sesión activa" if cookies_exist() else "No hay sesión. Ejecuta POST /auth primero.",
    }


@app.post("/scrape")
async def scrape(req: ScrapeRequest):
    username = req.username.strip().lstrip("@")
    if not username:
        raise HTTPException(status_code=400, detail="El username no puede estar vacío")
    if not cookies_exist():
        raise HTTPException(status_code=401, detail="No hay sesión activa. Ejecuta POST /auth primero.")
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(executor, scrape_profile, username)
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al extraer datos: {str(e)}")


@app.delete("/auth")
async def delete_session():
    if cookies_exist():
        os.remove("cookies.json")
        return {"success": True, "message": "Sesión eliminada."}
    return {"success": False, "message": "No había sesión activa."}


@app.get("/proxy/image")
async def proxy_image(url: str = Query(...)):
    """Proxy para imágenes de Instagram CDN que bloquean CORS."""
    if not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="URL inválida")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.instagram.com/",
            })
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
            return Response(content=resp.content, media_type=content_type)
    except Exception:
        raise HTTPException(status_code=502, detail="No se pudo obtener la imagen")
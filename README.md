# 📸 Instagram Public Scraper v3

Extractor de datos públicos de perfiles de Instagram usando **Playwright + FastAPI**, con un frontend integrado en HTML, CSS y JS puro.

---

## 🗂️ Estructura del Proyecto

```
instagram-scraper-v3/
├── backend/
│   ├── main.py           # API FastAPI y rutas
│   ├── scraper.py        # Lógica de extracción con Playwright
│   ├── auth.py           # Login interactivo manual y manejo de cookies
│   ├── requirements.txt  # Dependencias de Python
│   └── cookies.json      # Archivo generado al iniciar sesión
└── frontend/
    ├── index.html        # Interfaz web del usuario
    ├── style.css         # Estilos visuales
    └── app.js            # Lógica del cliente
```

---

## ⚙️ Instalación

### 1. Clonar o descomprimir el proyecto

### 2. Configurar entorno de Python

```bash
cd backend

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate       # En Linux/Mac
venv\Scripts\activate          # En Windows

# Instalar las dependencias necesarias
pip install -r requirements.txt

# Instalar el navegador Chromium requerido por Playwright
playwright install chromium
```

---

## 🚀 Uso

### Iniciar el servidor

```bash
cd backend
uvicorn main:app --reload --port 8000
```

- El **frontend web** estará disponible en: [http://localhost:8000](http://localhost:8000)
- La **documentación de la API (Swagger)** en: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📋 Flujo de Uso (Frontend / Backend)

### Paso 1 — Autenticación (Solo una vez)

El proyecto utiliza un sistema de **login manual interactivo** para evitar bloqueos por automatización.

1. Al presionar "Autenticar" en la interfaz (o mediante una llamada `POST /auth`), se abrirá una ventana de Chromium visible.
2. Inicia sesión en tu cuenta de Instagram manualmente (resolviendo cualquier Captcha o validación en 2 pasos si es necesario).
3. Una vez iniciada la sesión, la ventana se cerrará sola y tu sesión se guardará en `cookies.json`.
4. **No necesitas repetir este paso** a menos que tu sesión expire (error 401).

### Paso 2 — Extraer un perfil

Ingresa el nombre de usuario (ej. `instagram`) en el frontend o realiza un `POST /scrape`:

```http
POST /scrape
{
  "username": "instagram"
}
```

La respuesta contiene todos los datos públicos del perfil y sus publicaciones recientes.

---

## 🔗 Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/auth` | Abre ventana para login interactivo y guarda cookies |
| `GET`  | `/auth/status` | Verifica si existe una sesión activa (`cookies.json`) |
| `DELETE`| `/auth` | Elimina la sesión actual |
| `POST` | `/scrape` | Extrae los datos de un perfil público de Instagram |
| `GET`  | `/proxy/image` | Proxy de imágenes para eludir bloqueos de CORS en el frontend |
| `GET`  | `/` | Interfaz web integrada |
| `GET`  | `/docs` | Swagger UI interactivo |

---

## 🛡️ Características y Restricciones

- ✅ Extrae solo perfiles **públicos** de Instagram.
- ✅ Autenticación **manual y segura** minimizando riesgo de bloqueos.
- ✅ Uso de Playwright con un **User-Agent real**.
- ✅ Sesión persistente mediante almacenamiento de cookies locales.
- ✅ Proxy de imágenes nativo para poder previsualizarlas correctamente sin problemas de CORS.

---

## ⚠️ Notas Importantes

- Las sesiones de Instagram pueden expirar. Si experimentas problemas al extraer (o errores 401), vuelve a ejecutar el flujo de autenticación (`/auth`).
- No compartas ni subas tu archivo `cookies.json` a repositorios públicos, ya que contiene tu sesión activa.
- Instagram actualiza frecuentemente su estructura web (DOM), por lo que la lógica de extracción (`scraper.py`) puede requerir ajustes en el futuro para adaptarse a estos cambios.
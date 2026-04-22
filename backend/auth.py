import os
from playwright.sync_api import sync_playwright

COOKIES_PATH = "cookies.json"


def login_and_save_cookies(username: str, password: str):
    def log(msg):
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode("ascii", "replace").decode())
        with open("debug_log.txt", "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    with sync_playwright() as p:
        log("[AUTH] Iniciando Playwright para login manual...")
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        log("[AUTH] Navegando a Instagram...")
        page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        accept_cookie_banner(page)

        log("=========================================================")
        log("[!] ACCION REQUERIDA: INICIA SESION MANUALMENTE")
        log("Por favor, ve a la ventana del navegador que se acaba de abrir.")
        log("Haz click en 'Entrar' / 'Log In' y completa cualquier Captcha o verificación.")
        log("Esperando hasta 5 minutos a que inicies sesión...")
        log("=========================================================")

        # Esperar hasta 5 minutos (300,000 ms) a que el usuario inicie sesión y la URL cambie
        import time
        start_time = time.time()
        login_success = False
        
        while time.time() - start_time < 300:
            try:
                if page.is_closed():
                    log("[AUTH] La página fue cerrada por el usuario.")
                    break
                
                current_url = page.url
                # Consideramos éxito si va al home '/' o si pide verificación extra (challenge)
                if current_url == "https://www.instagram.com/" or "challenge" in current_url or "two_factor" in current_url:
                    login_success = True
                    break
                
                page.wait_for_timeout(2000)
            except Exception as e:
                log(f"[AUTH] Error durante el bucle de espera: {e}")
                break

        if not login_success:
            current = page.url if not page.is_closed() else "cerrada"
            log(f"[AUTH] Timeout o error esperando el login manual. URL actual: {current}")
            raise Exception(f"No se detectó el inicio de sesión después de 5 minutos. URL final: {current}")

        log("[AUTH] ✓ Login exitoso detectado por cambio de URL.")

        # Cerrar popups post-login (como "¿Guardar información?" o "Activar notificaciones")
        page.wait_for_timeout(3000)
        for text in ["Not Now", "Ahora no", "Not now"]:
            try:
                btn = page.locator(f'button:has-text("{text}"), div:has-text("{text}")[role="button"]').first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    page.wait_for_timeout(1000)
            except Exception:
                pass

        context.storage_state(path=COOKIES_PATH)
        log(f"[AUTH] ✓ Sesión guardada exitosamente en '{COOKIES_PATH}'")
        browser.close()

    return True


def accept_cookie_banner(page):
    for selector in [
        'button:has-text("Allow all cookies")',
        'button:has-text("Permitir todas las cookies")',
        'button:has-text("Accept All")',
        'button:has-text("Aceptar todo")',
        'button:has-text("Allow essential and optional cookies")',
        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
    ]:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=3000):
                btn.click()
                print("[AUTH] ✓ Banner de cookies aceptado")
                page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    return False


def cookies_exist() -> bool:
    return os.path.exists(COOKIES_PATH) and os.path.getsize(COOKIES_PATH) > 0
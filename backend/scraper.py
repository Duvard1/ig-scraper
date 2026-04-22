import re
from playwright.sync_api import sync_playwright
from auth import accept_cookie_banner, COOKIES_PATH, cookies_exist

REAL_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def scrape_profile(username: str) -> dict:
    if not cookies_exist():
        raise RuntimeError("No hay sesión guardada. Ejecuta el endpoint /auth primero.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=COOKIES_PATH,
            user_agent=REAL_USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
        )

        page = context.new_page()

        url = f"https://www.instagram.com/{username}/"
        print(f"[SCRAPER] Navegando a {url}")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        accept_cookie_banner(page)

        # Verificar si el perfil existe
        try:
            if page.locator('text="Sorry, this page isn\'t available."').is_visible(timeout=3000):
                browser.close()
                raise ValueError(f"El perfil @{username} no existe.")
        except Exception as e:
            if "ValueError" in type(e).__name__:
                raise
            pass

        # Verificar si es privado
        try:
            if page.locator('text="This Account is Private"').is_visible(timeout=3000):
                browser.close()
                raise ValueError(f"El perfil @{username} es privado.")
        except Exception as e:
            if "ValueError" in type(e).__name__:
                raise
            pass

        page.wait_for_timeout(2000)
        data = extract_profile_data(page, username)
        browser.close()

    return data


def extract_profile_data(page, username: str) -> dict:
    result = {
        "username": username,
        "full_name": None,
        "bio": None,
        "followers": None,
        "following": None,
        "posts_count": None,
        "is_verified": False,
        "profile_pic_url": None,
        "recent_posts": [],
    }

    # Estrategia 1: meta description
    try:
        meta_desc = page.evaluate(
            'document.querySelector(\'meta[name="description"]\')?.getAttribute("content") || ""'
        )
        print(f"[SCRAPER] Meta: {meta_desc[:100]}")

        followers_match = re.search(r"([\d,\.]+[KkMm]?)\s*Followers", meta_desc, re.IGNORECASE)
        following_match = re.search(r"([\d,\.]+[KkMm]?)\s*Following", meta_desc, re.IGNORECASE)
        posts_match    = re.search(r"([\d,\.]+[KkMm]?)\s*Posts", meta_desc, re.IGNORECASE)

        if followers_match: result["followers"]   = parse_number(followers_match.group(1))
        if following_match: result["following"]   = parse_number(following_match.group(1))
        if posts_match:     result["posts_count"] = parse_number(posts_match.group(1))
    except Exception as e:
        print(f"[SCRAPER] Error meta: {e}")

    # Estrategia 2: DOM
    try:
        for sel in ['header section h2', 'header h1', 'header h2', 'section h1']:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    result["full_name"] = el.inner_text().strip()
                    break
            except Exception:
                continue

        for sel in ['header section > div:last-child span', 'header section div span']:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    text = el.inner_text().strip()
                    if text and len(text) > 2:
                        result["bio"] = text
                        break
            except Exception:
                continue

        stats = page.locator('header section ul li')
        count = stats.count()
        if count >= 3:
            for i in range(count):
                try:
                    text = stats.nth(i).inner_text().strip()
                    num_match = re.search(r"([\d,\.]+[KkMm]?)", text)
                    if not num_match:
                        continue
                    num = parse_number(num_match.group(1))
                    tl = text.lower()
                    if "follower" in tl and result["followers"] is None:
                        result["followers"] = num
                    elif "following" in tl and result["following"] is None:
                        result["following"] = num
                    elif "post" in tl and result["posts_count"] is None:
                        result["posts_count"] = num
                except Exception:
                    pass

        try:
            pic = page.locator('header img').first
            if pic.is_visible(timeout=2000):
                result["profile_pic_url"] = pic.get_attribute("src")
        except Exception:
            pass

        try:
            result["is_verified"] = page.locator('[aria-label="Verified"]').is_visible(timeout=2000)
        except Exception:
            pass

    except Exception as e:
        print(f"[SCRAPER] Error DOM: {e}")

    result["recent_posts"] = extract_recent_posts(page)
    return result


def extract_recent_posts(page, max_posts: int = 3) -> list:
    posts = []
    try:
        # Instagram a veces cambia <article>, es más seguro buscar enlaces a posts/reels
        post_selector = 'a[href*="/p/"], a[href*="/reel/"]'
        page.wait_for_selector(post_selector, timeout=8000)
        page.wait_for_timeout(1500)

        post_links = page.locator(post_selector)
        count = min(post_links.count(), max_posts)
        print(f"[SCRAPER] Posts encontrados: {count}")

        for i in range(count):
            try:
                link = post_links.nth(i)
                href = link.get_attribute("href")
                post_url = f"https://www.instagram.com{href}" if href else None
                img = link.locator('img').first
                img_url, img_alt = None, None
                if img.is_visible(timeout=2000):
                    img_url = img.get_attribute("src")
                    img_alt = img.get_attribute("alt")
                if post_url:
                    posts.append({"post_url": post_url, "thumbnail_url": img_url, "alt_text": img_alt or ""})
            except Exception as e:
                print(f"[SCRAPER] Error post {i}: {e}")
    except Exception as e:
        print(f"[SCRAPER] Error posts: {e}")
    return posts


def parse_number(value: str) -> int:
    if not value:
        return 0
    value = value.strip().replace(",", "")
    for suffix, mult in {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.items():
        if value.lower().endswith(suffix):
            try:
                return int(float(value[:-1]) * mult)
            except Exception:
                return 0
    try:
        return int(float(value))
    except Exception:
        return 0
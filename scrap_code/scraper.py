from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


# ── DRIVER ───────────────────────────────────────────────────────

def create_driver():
    """Membuat Chrome WebDriver dalam mode headless."""
    opsi = Options()
    opsi.add_argument("--headless")
    opsi.add_argument("--disable-gpu")
    opsi.add_argument("--no-sandbox")
    opsi.add_argument("--disable-dev-shm-usage")
    opsi.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2
    })
    return webdriver.Chrome(options=opsi)


# ── URL UTILITIES ─────────────────────────────────────────────────

def normalize_url(url: str) -> str:
    """Tambahkan skema https jika belum ada."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def clean_url(base_url: str, href: str) -> str:
    """Jadikan URL absolut dan hilangkan fragment."""
    absolute = urljoin(base_url, href.strip())
    parsed = urlparse(absolute)
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{query}"


def is_same_domain(url: str, root_domain: str) -> bool:
    netloc = urlparse(url).netloc.replace("www.", "")
    return bool(netloc) and (netloc == root_domain or netloc.endswith("." + root_domain))


def is_likely_article_url(url: str) -> bool:
    path = urlparse(url).path.lower().strip("/")
    if not path:
        return False

    deny_tokens = (
        "tag/", "author/", "category/", "login", "register",
        "about", "contact", "privacy", "terms", "profile/",
        "user/", "account/", "search", "foto/", "photo/",
        "video/", "images/", "topics/", "topic/",
    )
    if any(token in path for token in deny_tokens):
        return False

    parts = [p for p in path.split("/") if p]
    hints = ("read", "story", "detail", "post", "news")
    has_slug = path.count("-") >= 2
    has_date_segment = any(re.fullmatch(r"20\d{2}", p) for p in parts)
    many_segments = len(parts) >= 3
    tail_looks_like_title = bool(parts) and len(parts[-1].split("-")) >= 3

    return (
        any(token in path for token in hints)
        or has_slug
        or (has_date_segment and many_segments)
        or (many_segments and tail_looks_like_title)
    )


# ── CONTENT EXTRACTION ────────────────────────────────────────────

_JUNK_WORDS = ("copyright", "all rights reserved", "baca juga", "komentar", "iklan")

_CONTAINER_SELECTORS = [
    "article",
    "[itemprop='articleBody']",
    ".article-content",
    ".post-content",
    ".entry-content",
    ".detail-content",
]


def get_article_content(driver) -> str:
    for selector in _CONTAINER_SELECTORS:
        for container in driver.find_elements(By.CSS_SELECTOR, selector):
            good = _filter_paragraphs(container.find_elements(By.TAG_NAME, "p"))
            if good:
                return "\n\n".join(good)

    # Fallback: semua <p> di halaman
    return "\n\n".join(
        _filter_paragraphs(driver.find_elements(By.TAG_NAME, "p"))
    )


def _filter_paragraphs(paragraphs) -> list:
    result = []
    for p in paragraphs:
        text = p.text.strip()
        if len(text) < 20:
            continue
        if any(word in text.lower() for word in _JUNK_WORDS):
            continue
        result.append(text)
    return result


def get_article_date(driver) -> str:
    selectors = [
        "meta[property='article:published_time']",
        "meta[name='pubdate']",
        "meta[name='publishdate']",
        "meta[name='date']",
        "time[datetime]",
        "article time",
        "time",
        ".read__time", ".tayang", ".date", ".post-date", ".artikel-date",
    ]
    for sel in selectors:
        for el in driver.find_elements(By.CSS_SELECTOR, sel):
            value = (
                el.get_attribute("datetime")
                or el.get_attribute("content")
                or el.get_attribute("innerText")
                or el.text
                or ""
            ).strip()
            if value:
                return value

    # Fallback: JSON-LD
    for s in driver.find_elements(By.CSS_SELECTOR, "script[type='application/ld+json']"):
        raw = (s.get_attribute("innerHTML") or "").strip()
        for key in ('"datePublished"', '"dateModified"'):
            idx = raw.find(key)
            if idx == -1:
                continue
            after = raw[idx + len(key):]
            colon = after.find(":")
            if colon == -1:
                continue
            candidate = after[colon + 1:].strip()
            if candidate.startswith('"'):
                end = candidate.find('"', 1)
                if end > 1:
                    return candidate[1:end].strip()
    return ""


# ── SCRAPING ──────────────────────────────────────────────────────

def scrap_article(url: str) -> dict | None:
    """
    Scrape satu artikel. Return dict dengan key judul/tanggal/url/konten,
    atau None jika gagal.
    """
    driver = create_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article, h1"))
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "p"))
        )
    except Exception:
        driver.quit()
        return None

    try:
        judul = driver.find_element(By.TAG_NAME, "h1").text.strip()
    except Exception:
        judul = ""

    tanggal = get_article_date(driver)
    konten = get_article_content(driver).strip()
    driver.quit()

    if not judul or not konten or len(konten) < 80:
        return None

    return {"judul": judul, "tanggal": tanggal, "url": url, "konten": konten}


def scrap_homepage(
    url: str,
    driver,
    progress_callback=None,
    log_callback=None,
    data_callback=None,
    max_links: int = 10,
    max_workers: int = 2,
) -> int:
    """
    Scrape semua artikel yang ditemukan dari halaman utama.

    Callbacks (opsional):
        progress_callback(int)   – persentase 0-100
        log_callback(str)        – pesan log
        data_callback(list)      – [no, judul, tanggal, url, konten_preview]
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    driver.get(url)
    domain = urlparse(url).netloc.replace("www.", "")
    links = set()

    for a in driver.find_elements(By.TAG_NAME, "a"):
        href = (a.get_attribute("href") or "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        candidate = clean_url(url, href)
        if not is_same_domain(candidate, domain):
            continue
        if not is_likely_article_url(candidate):
            continue
        links.add(candidate)
        if len(links) >= max_links:
            break

    log(f"[INFO] {len(links)} link artikel ditemukan.")

    if not links:
        return 0

    total_berhasil = 0
    total = len(links)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scrap_article, link): link for link in links}

        for i, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            pct = int(i / total * 100)
            if progress_callback:
                progress_callback(pct)

            if result:
                total_berhasil += 1
                log(f"[OK] {result['judul'][:80]}")
                if data_callback:
                    data_callback([
                        total_berhasil,
                        result["judul"],
                        result["tanggal"],
                        result["url"],
                        result["konten"],   # konten penuh tanpa truncasi
                    ])
            else:
                log(f"[SKIP] {futures[future]}")

    return total_berhasil


# ── CLI ENTRY POINT ───────────────────────────────────────────────

def main():
    url = normalize_url(input("Masukan link yang ingin anda scrap = "))
    if not url:
        print("URL tidak boleh kosong")
        return

    parsed_path = urlparse(url).path.strip("/")
    is_article_input = is_likely_article_url(url) and parsed_path != ""

    hasil = 0
    if is_article_input:
        result = scrap_article(url)
        if result:
            hasil = 1
            print("\n=== HASIL SCRAPING ===")
            print("Judul  :", result["judul"])
            print("Tanggal:", result["tanggal"])
            print("Link   :", result["url"])
            print("Isi    :", result["konten"][:500])

    if hasil == 0:
        driver = create_driver()
        try:
            hasil = scrap_homepage(url, driver)
        finally:
            driver.quit()

        if hasil == 0:
            if not is_article_input:
                single = scrap_article(url)
                if single:
                    print("\n=== HASIL SCRAPING ===")
                    print("Judul  :", single["judul"])
                    print("Tanggal:", single["tanggal"])
                    print("Link   :", single["url"])
                    print("Isi    :", single["konten"][:500])
                    return
            print("Artikel tidak ditemukan")


if __name__ == "__main__":
    main()

# Catatan: jika isi menampilkan "you don't have permission on this site",
# biasanya web menggunakan anti-bot/firewall.
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Membuat driver menjadi headless
def create_driver():
    opsi = Options()
    opsi.add_argument("--headless")
    opsi.add_argument("--disable-gpu")
    opsi.add_argument("--no-sandbox")
    opsi.add_argument("--disable-dev-shm-usage")

    prefs = {"profile.managed_default_content_settings.images": 2}
    opsi.add_experimental_option("prefs", prefs)

    return webdriver.Chrome(options=opsi)

#menambah https ke imput link yang tidak ada
def normalize_url(url):
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def clean_url(base_url, href):
    absolute = urljoin(base_url, href.strip())
    parsed = urlparse(absolute)
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{query}"


def is_same_domain(url, root_domain):
    netloc = urlparse(url).netloc.replace("www.", "")
    return bool(netloc) and (netloc == root_domain or netloc.endswith("." + root_domain))


def is_likely_article_url(url):
    path = urlparse(url).path.lower().strip("/")
    if not path:
        return False

    deny_tokens = (
        "tag/",
        "author/",
        "category/",
        "login",
        "register",
        "about",
        "contact",
        "privacy",
        "terms",
        "profile/",
        "user/",
        "account/",
        "search",
        "foto/",
        "photo/",
        "video/",
        "images/",
        "topics/",
        "topic/",
    )
    if any(token in path for token in deny_tokens):
        return False

    hints = ("read", "story", "detail", "post", "news")
    parts = [p for p in path.split("/") if p]
    many_segments = len(parts) >= 3
    has_slug = path.count("-") >= 2
    has_date_segment = any(re.fullmatch(r"20\d{2}", p) for p in parts)
    tail_looks_like_title = bool(parts) and len(parts[-1].split("-")) >= 3

    if any(token in path for token in hints):
        return True
    if has_slug:
        return True
    if has_date_segment and many_segments:
        return True
    if many_segments and tail_looks_like_title:
        return True
    return False


def get_article_content(driver):
    container_selectors = [
        "article",
        "[itemprop='articleBody']",
        ".article-content",
        ".post-content",
        ".entry-content",
        ".detail-content",
    ]
    junk_words = ("copyright", "all rights reserved", "baca juga", "komentar", "iklan")

    for selector in container_selectors:
        containers = driver.find_elements(By.CSS_SELECTOR, selector)
        for container in containers:
            paragraphs = container.find_elements(By.TAG_NAME, "p")
            good = []
            for p in paragraphs:
                text = p.text.strip()
                if len(text) < 20:
                    continue
                low = text.lower()
                if any(word in low for word in junk_words):
                    continue
                good.append(text)
            if good:
                return "\n\n".join(good)

    
    paragraphs = driver.find_elements(By.TAG_NAME, "p")
    good = []
    for p in paragraphs:
        text = p.text.strip()
        if len(text) < 20:
            continue
        low = text.lower()
        if "copyright" in low or "all rights reserved" in low:
            continue
        good.append(text)
    return "\n\n".join(good)


def get_article_date(driver):
    # Urutkan selector dari yang paling spesifik ke paling umum.
    selectors = [
        "meta[property='article:published_time']",
        "meta[name='pubdate']",
        "meta[name='publishdate']",
        "meta[name='date']",
        "time[datetime]",
        "article time",
        "time",
        ".read__time",
        ".tayang",
        ".date",
        ".post-date",
        ".artikel-date",
    ]

    for sel in selectors:
        nodes = driver.find_elements(By.CSS_SELECTOR, sel)
        for el in nodes:
            value = (
                el.get_attribute("datetime")
                or el.get_attribute("content")
                or el.get_attribute("innerText")
                or el.text
            )
            value = (value or "").strip()
            if value:
                return value

    scripts = driver.find_elements(By.CSS_SELECTOR, "script[type='application/ld+json']")
    for s in scripts:
        raw = (s.get_attribute("innerHTML") or "").strip()
        if not raw:
            continue
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


def scrap_article(url):
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
    except:
        judul = ""

    tanggal = get_article_date(driver)
    konten = get_article_content(driver).strip()

    driver.quit()

    if not judul or not konten or len(konten) < 80:
        return None

    return {
        "judul": judul,
        "tanggal": tanggal,
        "url": url,
        "konten": konten
    }


def scrap_homepage(url, driver):
    driver.get(url)
    domain = urlparse(url).netloc.replace("www.", "")
    links = set()

    a_tags = driver.find_elements(By.TAG_NAME, "a")
    for a in a_tags:
        href = (a.get_attribute("href") or "").strip()

        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue

        candidate = clean_url(url, href)

        if not is_same_domain(candidate, domain):
            continue

        if not is_likely_article_url(candidate):
            continue

        links.add(candidate)

        if len(links) >= 10:
            break

    print("Jumlah link ditemukan:", len(links))

    total_berhasil = 0

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(scrap_article, link) for link in links]

        for future in as_completed(futures):
            result = future.result()

            if result:
                total_berhasil += 1
                print("\n=== HASIL SCRAPING ===")
                print("Judul :", result["judul"])
                print("Tanggal:", result["tanggal"])
                print("Link :", result["url"])
                print("Isi :", result["konten"][:500])

    return total_berhasil


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
            print("Judul :", result["judul"])
            print("Tanggal:", result["tanggal"])
            print("Link :", result["url"])
            print("Isi :", result["konten"][:500])

    if hasil == 0:
        driver = create_driver()
        try:
            hasil = scrap_homepage(url, driver)
        finally:
            driver.quit()

        if hasil == 0 and not is_article_input:
            single = scrap_article(url)
            if single:
                print("\n=== HASIL SCRAPING ===")
                print("Judul :", single["judul"])
                print("Tanggal:", single["tanggal"])
                print("Link :", single["url"])
                print("Isi :", single["konten"][:500])
            else:
                print("Artikel tidak ditemukan")
        elif hasil == 0:
            print("Artikel tidak ditemukan")


if __name__ == "__main__":
    main()


# jika isi menampilkan "you dont have permission on this site", biasanya web pakai anti bot/firewall

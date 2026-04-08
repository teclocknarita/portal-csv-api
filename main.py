import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI

app = FastAPI(
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

HEADERS = {"User-Agent": USER_AGENT}

MAX_PAGES = 6


@app.get("/")
def root():
    return {"message": "ok"}


def fetch_html(url: str) -> str:
    res = requests.get(url, headers=HEADERS, timeout=20)
    res.raise_for_status()
    return res.text


def get_soup(url: str) -> BeautifulSoup:
    html = fetch_html(url)
    return BeautifulSoup(html, "html.parser")


def is_same_domain(base_url: str, target_url: str) -> bool:
    base_netloc = urlparse(base_url).netloc.replace("www.", "")
    target_netloc = urlparse(target_url).netloc.replace("www.", "")
    return base_netloc == target_netloc


def extract_clinic_name(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    og_site_name = soup.find("meta", attrs={"property": "og:site_name"})
    if og_site_name and og_site_name.get("content"):
        return og_site_name["content"].strip()

    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        title = re.split(r"[|\-｜]", title)[0].strip()
        return title

    return "医院名要確認"


def extract_candidate_pages(base_url: str, soup: BeautifulSoup) -> list[str]:
    candidates = [base_url]

    keywords = [
        "clinic", "about", "feature", "concept", "guide", "staff", "doctor",
        "院内", "医院", "特徴", "こだわり", "スタッフ", "院長", "設備", "アクセス",
        "初診", "診療案内", "clinic-tour"
    ]

    scored = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)

        if href.startswith("javascript:") or href.startswith("#"):
            continue

        full_url = urljoin(base_url, href)

        if not is_same_domain(base_url, full_url):
            continue

        low = full_url.lower()
        text_low = text.lower()

        score = 0
        for k in keywords:
            if k in low or k in text_low:
                score += 5

        if score > 0:
            scored.append((full_url, score))

    seen = set()
    unique = []
    for url, score in sorted(scored, key=lambda x: x[1], reverse=True):
        if url in seen:
            continue
        seen.add(url)
        unique.append(url)

    for u in unique[:MAX_PAGES - 1]:
        if u not in candidates:
            candidates.append(u)

    return candidates[:MAX_PAGES]


def normalize_url(page_url: str, src: str) -> str:
    return urljoin(page_url, src.strip())


def get_context_text(img_tag) -> str:
    texts = []

    alt = img_tag.get("alt", "")
    if alt:
        texts.append(alt)

    title = img_tag.get("title", "")
    if title:
        texts.append(title)

    parent = img_tag.parent
    if parent:
        parent_text = parent.get_text(" ", strip=True)
        if parent_text:
            texts.append(parent_text[:200])

    return " ".join(texts).strip()


def should_skip_image(img_url: str) -> bool:
    low = img_url.lower()

    skip_keywords = [
        "logo", "icon", "svg", "spacer", "blank", "loading", "banner",
        "btn", "button", "arrow", "line", "close", "menu"
    ]

    if any(k in low for k in skip_keywords):
        return True

    if low.endswith(".svg"):
        return True

    return False


def score_image(img_url: str, context: str, page_url: str) -> int:
    low = img_url.lower()
    ctx = context.lower()
    page_low = page_url.lower()

    score = 0

    # 写真っぽいURLを優先
    strong_positive = [
        "clinic_slider", "clinic_img", "slider", "gallery", "clinic",
        "interior", "exterior", "staff", "doctor", "microscope",
        "xray", "room", "waiting", "unit"
    ]
    for k in strong_positive:
        if k in low:
            score += 10

    # 文脈優先
    context_positive = [
        "外観", "院内", "受付", "待合", "診療室", "設備", "機器",
        "マイクロスコープ", "レントゲン", "院長", "スタッフ",
        "駐車場", "キッズ", "医院紹介"
    ]
    for k in context_positive:
        if k.lower() in ctx:
            score += 8

    # ページ自体の文脈
    page_positive = [
        "clinic", "about", "feature", "staff", "doctor", "guide",
        "医院", "院内", "特徴", "設備", "スタッフ", "院長"
    ]
    for k in page_positive:
        if k in page_low:
            score += 4

    # 画像拡張子
    if low.endswith(".jpg") or low.endswith(".jpeg") or low.endswith(".png") or low.endswith(".webp"):
        score += 3

    # 弱そうなもの
    weak_negative = [
        "thumbnail", "thumb", "ogp", "og-image", "favicon"
    ]
    for k in weak_negative:
        if k in low:
            score -= 8

    return score


def collect_images_from_page(page_url: str) -> list[dict]:
    soup = get_soup(page_url)
    images = []

    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        if src.startswith("data:"):
            continue

        full_url = normalize_url(page_url, src)
        if should_skip_image(full_url):
            continue

        context = get_context_text(img)
        score = score_image(full_url, context, page_url)

        images.append({
            "url": full_url,
            "alt": img.get("alt", "").strip(),
            "context": context,
            "page_url": page_url,
            "score": score
        })

    return images


def dedupe_images(images: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for item in sorted(images, key=lambda x: x["score"], reverse=True):
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        result.append(item)

    return result


def classify_image(item: dict, index: int = 0) -> str:
    text = f"{item['url']} {item['alt']} {item['context']} {item['page_url']}".lower()

    if any(k in text for k in ["院長", "doctor", "dr.", "dr ", "staff", "スタッフ", "profile"]):
        return "スタッフ"

    if any(k in text for k in ["microscope", "マイクロスコープ", "レントゲン", "xray", "ct", "設備", "機器", "unit"]):
        return "設備"

    if any(k in text for k in ["院内", "受付", "待合", "診療室", "interior", "room", "waiting"]):
        return "院内"

    if any(k in text for k in ["外観", "駐車場", "exterior", "building", "facade"]):
        return "外観"

    if index == 0:
        return "外観"
    if index in [1, 2]:
        return "院内"
    return "設備"


def pick_top_images(images: list[dict]) -> list[dict]:
    selected = []
    for i, item in enumerate(images[:8]):
        selected.append({
            "slot": i + 1,
            "category": classify_image(item, i),
            "image_url": item["url"]
        })
    return selected


def find_best_image(images: list[dict], keywords: list[str]) -> str | None:
    for item in images:
        text = f"{item['url']} {item['alt']} {item['context']} {item['page_url']}".lower()
        if any(k.lower() in text for k in keywords):
            return item["url"]
    return None


def build_points(images: list[dict]) -> list[dict]:
    microscope = find_best_image(images, ["microscope", "マイクロスコープ", "設備"])
    parking = find_best_image(images, ["駐車場", "外観", "building", "facade"])
    kids = find_best_image(images, ["キッズ", "kids", "院内", "待合"])

    return [
        {
            "title": "精密な診査・診断",
            "body": "設備を活用し、細部まで確認しながら丁寧な診療に努めています。",
            "image_url": microscope
        },
        {
            "title": "通いやすい環境づくり",
            "body": "外観やアクセス面にも配慮し、通院しやすい環境づくりを大切にしています。",
            "image_url": parking
        },
        {
            "title": "院内環境への配慮",
            "body": "患者さまが落ち着いて通いやすいよう、院内環境にも配慮しています。",
            "image_url": kids
        }
    ]


def build_features(images: list[dict]) -> list[dict]:
    microscope = find_best_image(images, ["microscope", "マイクロスコープ"])
    xray = find_best_image(images, ["xray", "レントゲン", "ct"])
    interior = find_best_image(images, ["院内", "受付", "待合", "診療室"])

    return [
        {
            "title": "診療設備への配慮",
            "body": "設備を活用し、丁寧でわかりやすい診療につなげています。",
            "image_url": microscope
        },
        {
            "title": "状態把握を支える設備",
            "body": "お口の状態を確認し、適切な診療につなげるための設備を整えています。",
            "image_url": xray
        },
        {
            "title": "通いやすい院内環境",
            "body": "患者さまが安心して来院しやすいよう、院内環境にも配慮しています。",
            "image_url": interior
        }
    ]


def extract_phone(text: str) -> str:
    patterns = [
        r'0\d{1,4}-\d{1,4}-\d{4}',
        r'0\d{9,10}'
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(0)
    return ""


def extract_address(text: str) -> str:
    m = re.search(r'〒?\d{3}-\d{4}.{0,80}', text)
    if m:
        return m.group(0).strip()
    return ""


@app.post("/draft")
def draft(payload: dict):
    url = payload.get("url")

    if not url:
        return {
            "clinic_name": "URL未指定",
            "top_images": [],
            "points": [],
            "director": {"name": "", "image_url": None},
            "staff": [],
            "features": [],
            "warnings": ["URLが指定されていません"]
        }

    try:
        top_soup = get_soup(url)
        clinic_name = extract_clinic_name(top_soup)

        candidate_pages = extract_candidate_pages(url, top_soup)

        all_images = []
        page_texts = []

        for page_url in candidate_pages:
            try:
                page_soup = get_soup(page_url)
                page_texts.append(page_soup.get_text(" ", strip=True)[:5000])
                all_images.extend(collect_images_from_page(page_url))
            except Exception:
                continue

        all_images = dedupe_images(all_images)

        top_images = pick_top_images(all_images)
        director_image = find_best_image(all_images, ["院長", "doctor", "dr", "profile", "スタッフ"])
        points = build_points(all_images)
        features = build_features(all_images)

        merged_text = " ".join(page_texts)
        phone = extract_phone(merged_text)
        address = extract_address(merged_text)

        warnings = []
        warnings.append(f"巡回ページ数: {len(candidate_pages)}")
        warnings.append("画像分類は自動判定のため確認が必要です")

        if not top_images:
            warnings.append("TOP画像を取得できませんでした")
        if not director_image:
            warnings.append("院長写真は要確認です")
        if not phone:
            warnings.append("電話番号は要確認です")
        if not address:
            warnings.append("住所は要確認です")

        return {
            "clinic_name": clinic_name,
            "top_images": top_images,
            "points": points,
            "director": {
                "name": "要確認",
                "image_url": director_image
            },
            "staff": [
                {
                    "name": "",
                    "comment": "スタッフ写真が見つからない場合は文章のみで掲載してください。",
                    "image_url": None
                }
            ],
            "features": features,
            "phone": phone,
            "address": address,
            "warnings": warnings
        }

    except Exception as e:
        return {
            "clinic_name": "取得失敗",
            "top_images": [],
            "points": [],
            "director": {"name": "", "image_url": None},
            "staff": [],
            "features": [],
            "warnings": [f"エラー: {str(e)}"]
        }


@app.post("/generate-csv")
def generate_csv(payload: dict):
    return {
        "csv_file_url": "https://example.com/sample.csv",
        "xlsx_file_url": "https://example.com/sample.xlsx",
        "warnings": ["CSV生成は未実装です"]
    }

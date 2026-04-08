import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI

app = FastAPI(
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


@app.get("/")
def root():
    return {"message": "ok"}


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
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        }

        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")

        # -------------------------
        # 医院名取得（title + h1）
        # -------------------------
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        h1 = soup.find("h1")
        clinic_name = h1.text.strip() if h1 and h1.text else title or "不明"

        # -------------------------
        # 画像取得
        # -------------------------
        imgs = soup.find_all("img")
        image_urls = []

        for img in imgs:
            src = img.get("src")
            alt = img.get("alt", "").lower()

            if not src:
                continue

            src_lower = src.lower()

            # ❌ 除外条件
            if (
                "logo" in src_lower
                or "icon" in src_lower
                or "svg" in src_lower
                or "banner" in src_lower
                or "loading" in src_lower
                or "spacer" in src_lower
                or "blank" in src_lower
            ):
                continue

            if src_lower.endswith(".svg"):
                continue

            if src.startswith("data:"):
                continue

            # 相対URL対応
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = url.rstrip("/") + src
            elif not src.startswith("http"):
                src = url.rstrip("/") + "/" + src.lstrip("/")

            if src not in image_urls:
                image_urls.append((src, alt))

        # -------------------------
        # 画像分類（ここが重要）
        # -------------------------
        top_images = []

        for i, (img_url, alt) in enumerate(image_urls[:6]):

            url_lower = img_url.lower()
            alt_lower = alt.lower()

            # 👇 意味ベース分類
            if any(k in url_lower or k in alt_lower for k in ["staff", "doctor", "院長", "スタッフ"]):
                category = "スタッフ"

            elif any(k in url_lower or k in alt_lower for k in ["microscope", "equipment", "機器", "設備"]):
                category = "設備"

            elif any(k in url_lower or k in alt_lower for k in ["room", "clinic", "院内", "待合"]):
                category = "院内"

            elif any(k in url_lower or k in alt_lower for k in ["外観", "building"]):
                category = "外観"

            else:
                # fallback（順番）
                if i == 0:
                    category = "外観"
                elif i == 1:
                    category = "院内"
                else:
                    category = "設備"

            top_images.append({
                "slot": i + 1,
                "category": category,
                "image_url": img_url
            })

        # -------------------------
        # 警告
        # -------------------------
        warnings = []

        if not top_images:
            warnings.append("画像を取得できませんでした")

        warnings.extend([
            "ポイント・特徴の情報が不足しています",
            "スタッフ情報が限定的です",
            "画像分類は自動判定のため確認が必要です"
        ])

        return {
            "clinic_name": clinic_name,
            "top_images": top_images,
            "points": [],
            "director": {"name": "", "image_url": None},
            "staff": [],
            "features": [],
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

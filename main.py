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

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # タイトル取得
        title = soup.title.string.strip() if soup.title and soup.title.string else "不明"

        # 画像抽出
        imgs = soup.find_all("img")
        image_urls = []

        for img in imgs:
            src = img.get("src")

            if not src:
                continue

            src_lower = src.lower()

            # 不要そうな画像を除外
            exclude_keywords = [
                "logo",
                "icon",
                "svg",
                "banner",
                "loading",
                "spacer",
                "blank",
            ]
            if any(keyword in src_lower for keyword in exclude_keywords):
                continue

            # data:image は除外
            if src.startswith("data:"):
                continue

            # 相対パスを絶対URL化
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = url.rstrip("/") + src
            elif src.startswith("./"):
                src = url.rstrip("/") + "/" + src.lstrip("./")
            elif not src.startswith("http"):
                src = url.rstrip("/") + "/" + src.lstrip("/")

            # 重複除外
            if src not in image_urls:
                image_urls.append(src)

        # 上位3枚をTOP画像にする
        top_images = [
            {
                "slot": i + 1,
                "category": "外観",
                "image_url": img_url
            }
            for i, img_url in enumerate(image_urls[:3])
        ]

        warnings = []
        if not top_images:
            warnings.append("TOP画像を取得できませんでした")
        warnings.extend([
            "ポイント・特徴の情報が不足しています",
            "スタッフ情報が限定的です",
            "TOP画像・各画像が仮分類のため差し替えが必要です"
        ])

        return {
            "clinic_name": title,
            "top_images": top_images,
            "points": [],
            "director": {
                "name": "",
                "image_url": None
            },
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
        "warnings": ["CSV生成はまだダミーです"]
    }

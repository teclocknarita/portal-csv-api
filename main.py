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

    try:
        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")

        # タイトル
        title = soup.title.string if soup.title else "不明"

        # 👇 画像1枚だけ取得（最初のimg）
        img_tag = soup.find("img")
        img_url = img_tag["src"] if img_tag and img_tag.get("src") else None

    except Exception as e:
        return {
            "clinic_name": "取得失敗",
            "warnings": [str(e)]
        }

    return {
        "clinic_name": title,
        "top_images": [
            {
                "slot": 1,
                "category": "外観",
                "image_url": img_url
            }
        ] if img_url else [],
        "points": [],
        "director": {"name": "", "image_url": None},
        "staff": [],
        "features": [],
        "warnings": []
    }

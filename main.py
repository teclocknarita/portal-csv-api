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

        # タイトル取得
        title = soup.title.string if soup.title else "タイトル不明"

    except Exception as e:
        return {
            "clinic_name": "取得失敗",
            "warnings": [str(e)]
        }

    return {
        "clinic_name": title,
        "top_images": [],
        "points": [],
        "director": {"name": "", "image_url": None},
        "staff": [],
        "features": [],
        "warnings": []
    }

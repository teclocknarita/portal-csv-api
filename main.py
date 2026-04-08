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
    return {
        "clinic_name": "吉本歯科クリニック",
        "top_images": [
            {"slot": 1, "category": "外観", "image_url": "https://example.com/img1.jpg"},
            {"slot": 2, "category": "院内", "image_url": "https://example.com/img2.jpg"}
        ],
        "points": [
            {
                "title": "精密な診査・診断",
                "body": "マイクロスコープを活用した精密治療",
                "image_url": "https://example.com/p1.jpg"
            }
        ],
        "director": {
            "name": "吉本 寛規",
            "image_url": "https://example.com/doc.jpg"
        },
        "staff": [
            {
                "name": "",
                "comment": "丁寧な対応を心がけています",
                "image_url": None
            }
        ],
        "features": [
            {
                "title": "マイクロスコープ",
                "body": "精密治療を支える設備",
                "image_url": "https://example.com/f1.jpg"
            }
        ],
        "warnings": []
    }

@app.post("/generate-csv")
def generate_csv(payload: dict):
    return {
        "csv_file_url": "https://example.com/sample.csv",
        "xlsx_file_url": "https://example.com/sample.xlsx",
        "warnings": []
    }

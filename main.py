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
        "clinic_name": "テスト医院",
        "top_images": [],
        "points": [],
        "director": {"name": "", "image_url": None},
        "staff": [],
        "features": [],
        "warnings": []
    }

@app.post("/generate-csv")
def generate_csv(payload: dict):
    return {
        "csv_file_url": "https://example.com/sample.csv",
        "xlsx_file_url": "https://example.com/sample.xlsx",
        "warnings": []
    }

imgs = soup.find_all("img")

image_urls = []

for img in imgs:
    src = img.get("src")

    if not src:
        continue

    # 小さい画像・アイコン除外
    if "logo" in src or "icon" in src or "svg" in src:
        continue

    # 相対パス対応
    if src.startswith("/"):
        src = url.rstrip("/") + src

    image_urls.append(src)

# 上位3枚だけ使う
top_images = [
    {"slot": i+1, "category": "外観", "image_url": img}
    for i, img in enumerate(image_urls[:3])
]

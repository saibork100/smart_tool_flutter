import requests

url = "http://127.0.0.1:8000/detect"

with open(r"E:\photo coliction\dataset\val\4mm_10mm\IMG_3042 10mm.jpg", "rb") as f:
    response = requests.post(url, files={"file": ("image.jpg", f, "image/jpeg")})

print("Status:", response.status_code)
print("Response:", response.json())

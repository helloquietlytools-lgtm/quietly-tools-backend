import requests

def upload(token, title, html):
    headers = {
        "Authorization": f"Bearer {token.access_token}"
    }

    metadata = {
        "name": f"{title}.html",
        "mimeType": "text/html"
    }

    files = {
        "metadata": ("metadata", str(metadata), "application/json"),
        "file": ("file.html", html, "text/html"),
    }

    requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
        headers=headers,
        files=files,
    )

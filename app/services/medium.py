import requests

def publish(token, title, markdown):
    user = requests.get(
        "https://api.medium.com/v1/me",
        headers={"Authorization": f"Bearer {token.access_token}"}
    ).json()["data"]["id"]

    requests.post(
        f"https://api.medium.com/v1/users/{user}/posts",
        headers={
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json"
        },
        json={
            "title": title,
            "contentFormat": "markdown",
            "content": markdown,
            "publishStatus": "draft"
        }
    )

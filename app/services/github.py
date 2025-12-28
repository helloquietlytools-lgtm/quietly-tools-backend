import base64
import requests

def upload(token, title, markdown):
    content = base64.b64encode(markdown.encode()).decode()

    requests.put(
        "https://api.github.com/repos/OWNER/REPO/contents/docs/{}.md".format(title),
        headers={
            "Authorization": f"token {token.access_token}",
            "Accept": "application/vnd.github+json"
        },
        json={
            "message": "MindMark export",
            "content": content,
            "branch": "main"
        }
    )

"""6단계: YouTube Data API 업로드. 최초 1회 브라우저 로그인 → token.json 저장."""
from pathlib import Path
from .common import load_config, ROOT, log

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _service(cfg):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    tok = ROOT / cfg["youtube"]["token_file"]
    creds = Credentials.from_authorized_user_file(tok, SCOPES) if tok.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(ROOT / cfg["youtube"]["client_secret"], SCOPES)
            creds = flow.run_local_server(port=0)
        tok.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload(script: dict, video: Path, thumb: Path) -> str:
    from googleapiclient.http import MediaFileUpload
    cfg = load_config()
    yt = _service(cfg)
    is_shorts = cfg.get("current_format") == "shorts"
    title = script["title"][:90]
    if is_shorts and "#Shorts" not in title and "#shorts" not in title:
        title = f"{title} #Shorts"
    desc = script["description"]
    if is_shorts and "#Shorts" not in desc and "#shorts" not in desc:
        desc = f"{desc}\n\n#Shorts #쇼츠"

    tags = list(dict.fromkeys(cfg["youtube"]["default_tags"] + script.get("tags", []) + (["Shorts", "쇼츠"] if is_shorts else [])))[:30]

    body = {
        "snippet": {"title": title, "description": desc,
                    "tags": tags,
                    "categoryId": cfg["youtube"]["category_id"], "defaultLanguage": "ko"},
        "status": {"privacyStatus": cfg["youtube"]["privacy"], "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status: log.info(f"업로드 {int(status.progress()*100)}%")
    vid = resp["id"]
    yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
    url = f"https://youtu.be/{vid}"
    log.info(f"업로드 완료: {url}")
    return url

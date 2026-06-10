# качаємо mp3 з драйву та записуємо результати назад
# треба credentials.json і доступи до папки
import io
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

def _get_svc():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def download_audio(dir_id, dest):
    Path(dest).mkdir(parents=True, exist_ok=True)
    svc = _get_svc()
    q = f"'{dir_id}' in parents and mimeType contains 'audio'"
    items = svc.files().list(q=q, fields="files(id,name)", pageSize=1000).execute().get("files", [])
    
    for item in items:
        target = Path(dest) / item["name"]
        if target.exists():
            continue
        
        req = svc.files().get_media(fileId=item["id"])
        with io.FileIO(target, "wb") as fh:
            dl = MediaIoBaseDownload(fh, req)
            done = False
            while not done:
                _, done = dl.next_chunk()
    return len(items)

def upload_transcript(dir_id, file_path):
    svc = _get_svc()
    meta = {"name": Path(file_path).name, "parents": [dir_id]}
    media = MediaFileUpload(file_path, mimetype="text/plain")
    svc.files().create(body=meta, media_body=media, fields="id").execute()
import os
import io
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_creds():
    creds = None
    # читаємо кешований токен
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception:
            pass
            
    # якщо токен невалідний — оновлюємо або запускаємо авторизацію
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            
        # кешуємо токен
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def _get_svc():
    return build("drive", "v3", credentials=get_creds())

def download_audio(src_folder_id, dest):
    Path(dest).mkdir(parents=True, exist_ok=True)
    svc = _get_svc()
    q = f"'{src_folder_id}' in parents and mimeType contains 'audio' and trashed = false"
    items = svc.files().list(q=q, fields="files(id,name)", pageSize=1000).execute().get("files", [])
    
    downloaded = 0
    for item in items:
        target = Path(dest) / item["name"]
        if target.exists():
            continue
            
        print(f"  завантажую {item['name']}...")
        req = svc.files().get_media(fileId=item["id"])
        with io.FileIO(target, "wb") as fh:
            dl = MediaIoBaseDownload(fh, req)
            done = False
            while not done:
                _, done = dl.next_chunk()
        downloaded += 1
    return downloaded

def ensure_work_folder(name):
    svc = _get_svc()
    q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    items = svc.files().list(q=q, fields="files(id)", pageSize=1).execute().get("files", [])
    
    if items:
        return items[0]["id"]
        
    # створюємо папку якщо її немає
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    folder = svc.files().create(body=meta, fields="id").execute()
    return folder["id"]

def upload_or_update_file(folder_id, file_path, mimetype):
    svc = _get_svc()
    name = Path(file_path).name
    
    # шукаємо файл у цій папці
    q = f"'{folder_id}' in parents and name = '{name}' and trashed = false"
    items = svc.files().list(q=q, fields="files(id)", pageSize=1).execute().get("files", [])
    
    media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
    
    if items:
        # оновлюємо вміст існуючого
        fid = items[0]["id"]
        svc.files().update(fileId=fid, media_body=media).execute()
        return fid
    else:
        # створюємо новий файл
        meta = {"name": name, "parents": [folder_id]}
        file = svc.files().create(body=meta, media_body=media, fields="id").execute()
        return file["id"]
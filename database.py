import json
import streamlit as st
from supabase import create_client

BUCKET = "uploads"

@st.cache_resource
def get_db():
    """Buat koneksi Supabase sekali, di-cache selama app berjalan."""
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

def init_and_migrate_db():
    """No-op: tabel sudah dibuat via Supabase dashboard."""
    pass

def fetch_tasks():
    result = get_db().table("tasks").select("*").order("id", desc=True).execute()
    return result.data or []

def fetch_task_by_id(task_id):
    result = get_db().table("tasks").select("*").eq("id", task_id).execute()
    return result.data[0] if result.data else None

def add_task(title, assignee, deadline, platform, status, asset_link, checklist_dict, content_type, description=""):
    get_db().table("tasks").insert({
        "title": title,
        "assignee": assignee,
        "deadline": deadline,
        "platform": platform,
        "status": status,
        "asset_link": asset_link,
        "checklist": json.dumps(checklist_dict),
        "content_type": content_type,
        "description": description
    }).execute()

def update_task_details(task_id, title, assignee, deadline, platform, status, content_type, asset_link, description):
    get_db().table("tasks").update({
        "title": title,
        "assignee": assignee,
        "deadline": deadline,
        "platform": platform,
        "status": status,
        "content_type": content_type,
        "asset_link": asset_link,
        "description": description
    }).eq("id", task_id).execute()

def update_status(task_id, new_status):
    get_db().table("tasks").update({"status": new_status}).eq("id", task_id).execute()

def update_checklist(task_id, checklist_dict):
    get_db().table("tasks").update({"checklist": json.dumps(checklist_dict)}).eq("id", task_id).execute()

def update_media_path(task_id, column_name, file_path):
    get_db().table("tasks").update({column_name: file_path}).eq("id", task_id).execute()

# ─── Supabase Storage Helpers ─────────────────────────────────────────────────

def get_public_url(storage_path: str) -> str:
    """Bangun public URL Supabase Storage secara manual — lebih reliable antar versi."""
    if not storage_path:
        return ""
    if storage_path.startswith("http"):
        return storage_path
    base_url = st.secrets["SUPABASE_URL"].rstrip("/")
    return f"{base_url}/storage/v1/object/public/{BUCKET}/{storage_path}"

def upload_file(file_bytes: bytes, storage_path: str, content_type: str = "application/octet-stream") -> str:
    """Upload file ke Supabase Storage, return storage path."""
    try:
        get_db().storage.from_(BUCKET).upload(
            storage_path,
            file_bytes,
            {"content-type": content_type, "upsert": "true"}
        )
        return storage_path
    except Exception as e:
        err_msg = str(e)
        if "Bucket not found" in err_msg or "NoSuchBucket" in err_msg or "404" in err_msg:
            raise RuntimeError(
                f"Bucket '{BUCKET}' belum dibuat di Supabase Storage. "
                f"Silakan buat bucket bernama '{BUCKET}' (centang Public) di Supabase Dashboard -> Storage."
            ) from e
        elif "row-level security" in err_msg.lower() or "unauthorized" in err_msg.lower() or "403" in err_msg:
            raise RuntimeError(
                f"Izin akses Storage ditolak (RLS Policy). "
                f"Pastikan sudah menambahkan Storage Policy (INSERT & SELECT) untuk publik pada bucket '{BUCKET}'."
            ) from e
        raise e

def delete_file_from_storage(storage_path: str):
    """Hapus file dari Supabase Storage. Aman dipanggil dengan path kosong."""
    if not storage_path:
        return
    try:
        path = storage_path
        if storage_path.startswith("http"):
            marker = f"/{BUCKET}/"
            idx = storage_path.find(marker)
            if idx != -1:
                path = storage_path[idx + len(marker):].split("?")[0]
        get_db().storage.from_(BUCKET).remove([path])
    except Exception:
        pass

def delete_task(task_id):
    """Hapus task dari DB dan file medianya dari Storage."""
    task = fetch_task_by_id(task_id)
    if task:
        delete_file_from_storage(task.get("thumbnail_path", ""))
        delete_file_from_storage(task.get("video_path", ""))
    get_db().table("tasks").delete().eq("id", task_id).execute()
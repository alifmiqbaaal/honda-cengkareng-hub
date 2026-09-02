import sqlite3
import json
import os

DB_NAME = "production.db"

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_and_migrate_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            assignee TEXT NOT NULL,
            deadline TEXT,
            platform TEXT,
            status TEXT NOT NULL,
            asset_link TEXT DEFAULT '',
            checklist TEXT DEFAULT '{}',
            thumbnail_path TEXT DEFAULT '',
            video_path TEXT DEFAULT '',
            content_type TEXT DEFAULT 'Video',
            description TEXT DEFAULT ''
        )
    """)
    conn.commit()

    cursor.execute("PRAGMA table_info(tasks)")
    columns = [row["name"] for row in cursor.fetchall()]
    
    fields_to_add = [
        ("asset_link", "TEXT DEFAULT ''"),
        ("checklist", "TEXT DEFAULT '{}'"),
        ("thumbnail_path", "TEXT DEFAULT ''"),
        ("video_path", "TEXT DEFAULT ''"),
        ("content_type", "TEXT DEFAULT 'Video'"),
        ("description", "TEXT DEFAULT ''")
    ]
    
    for col_name, col_type in fields_to_add:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
            
    conn.commit()
    conn.close()

def fetch_tasks():
    conn = get_db()
    tasks = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(t) for t in tasks]

def fetch_task_by_id(task_id):
    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(task) if task else None

def add_task(title, assignee, deadline, platform, status, asset_link, checklist_dict, content_type, description=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO tasks (title, assignee, deadline, platform, status, asset_link, checklist, content_type, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (title, assignee, deadline, platform, status, asset_link, json.dumps(checklist_dict), content_type, description)
    )
    conn.commit()
    conn.close()

def update_task_details(task_id, title, assignee, deadline, platform, status, content_type, asset_link, description):
    conn = get_db()
    conn.execute(
        "UPDATE tasks SET title = ?, assignee = ?, deadline = ?, platform = ?, status = ?, content_type = ?, asset_link = ?, description = ? WHERE id = ?",
        (title, assignee, deadline, platform, status, content_type, asset_link, description, task_id)
    )
    conn.commit()
    conn.close()

def update_status(task_id, new_status):
    conn = get_db()
    conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
    conn.commit()
    conn.close()

def update_checklist(task_id, checklist_dict):
    conn = get_db()
    conn.execute("UPDATE tasks SET checklist = ? WHERE id = ?", (json.dumps(checklist_dict), task_id))
    conn.commit()
    conn.close()

def update_media_path(task_id, column_name, file_path):
    conn = get_db()
    conn.execute(f"UPDATE tasks SET {column_name} = ? WHERE id = ?", (file_path, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = get_db()
    task = conn.execute("SELECT thumbnail_path, video_path FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task:
        if task["thumbnail_path"] and os.path.exists(task["thumbnail_path"]):
            os.remove(task["thumbnail_path"])
        if task["video_path"] and os.path.exists(task["video_path"]):
            os.remove(task["video_path"])
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
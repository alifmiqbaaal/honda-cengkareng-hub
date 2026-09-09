import streamlit as st
import json
import os
import calendar
from datetime import date, datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import database as db

# 1. Inisialisasi & Setup Halaman (Sidebar dihilangkan total)
st.set_page_config(page_title="Content Production Hub", layout="wide", initial_sidebar_state="collapsed")

# Session state untuk pelacakan navigasi dan notifikasi
if "current_nav" not in st.session_state:
    st.session_state.current_nav = "Home"
if "selected_cal_date" not in st.session_state:
    st.session_state.selected_cal_date = date.today().isoformat()
if "success_msg" not in st.session_state:
    st.session_state.success_msg = None
if "active_task_id" not in st.session_state:
    st.session_state.active_task_id = None
if "keep_dialog_open" not in st.session_state:
    st.session_state.keep_dialog_open = False
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

# Render notifikasi toast jika ada pesan sukses dari action sebelumnya
if st.session_state.success_msg:
    st.toast(st.session_state.success_msg, icon="✨")
    st.session_state.success_msg = None

# Deteksi penutupan dialog via tombol X (bukan save/delete)
_prev_dialog_seen = st.session_state.pop("_dialog_seen", False)
if _prev_dialog_seen and not st.session_state.get("keep_dialog_open", False):
    st.session_state.active_task_id = None

# Autorefresh hanya aktif ketika tidak ada dialog yang sedang terbuka
if st.session_state.active_task_id is None:
    st_autorefresh(interval=5000, key="apple_glass_autorefresh")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
db.init_and_migrate_db()

# 2. Muat Styling Eksternal & CSS Top Navbar
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
    <style>
        /* Sembunyikan sidebar bawaan dan tombol lipatnya */
        section[data-testid="stSidebar"],
        div[data-testid="collapsedControl"],
        button[data-testid="stSidebarCollapseButton"] {
            display: none !important;
            visibility: hidden !important;
        }

        /* Rapikan jarak batas atas layar */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }

        /* Pastikan label tombol menu navbar selalu terbaca jelas */
        div[data-testid="stRadio"] label p,
        div[data-testid="stRadio"] label span {
            color: #f5f5f7 !important;
            font-size: 13.5px !important;
            font-weight: 500 !important;
            margin: 0 !important;
            visibility: visible !important;
        }

        /* Efek hover teks navbar */
        div[data-testid="stRadio"] label:hover p {
            color: #ffd60a !important;
        }

        /* ========================================================= */
        /* STYLING GRID TOMBOL KALENDER SERAGAM & PRESISI            */
        /* ========================================================= */
        div[data-testid="stButton"] button[kind="secondary"],
        div[data-testid="stButton"] button[kind="primary"] {
            box-sizing: border-box !important;
            border-radius: 12px !important;
            height: 50px !important;
            min-height: 50px !important;
            max-height: 50px !important;
            width: 100% !important;
            margin: 0 !important;
            transform: none !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }

        /* Tombol Tanggal Default (Tidak Dipilih) */
        div[data-testid="stButton"] button[kind="secondary"] {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            color: #f5f5f7 !important;
            font-size: 15px !important;
            font-weight: 600 !important;
        }

        div[data-testid="stButton"] button[kind="secondary"]:hover {
            border-color: rgba(255, 214, 10, 0.4) !important;
            background: rgba(255, 255, 255, 0.08) !important;
            color: #ffd60a !important;
        }

        /* Tombol Tanggal Aktif Terpilih (Emas menyala, ukuran tetap sejajar rata) */
        div[data-testid="stButton"] button[kind="primary"] {
            background: linear-gradient(135deg, #ffd60a 0%, #f59e0b 100%) !important;
            border: 1px solid #ffd60a !important;
            box-shadow: 0 0 16px rgba(255, 214, 10, 0.3) !important;
        }

        div[data-testid="stButton"] button[kind="primary"] p {
            color: #000000 !important;
            font-weight: 800 !important;
            font-size: 15px !important;
        }

        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: linear-gradient(135deg, #ffe033 0%, #fbbf24 100%) !important;
            border-color: #ffd60a !important;
        }

        /* FIX MULTISELECT: HILANGKAN BULATAN KURSOR HITAM */
        div[data-testid="stMultiSelect"] span[data-baseweb="tag"] + div {
            background: transparent !important;
            box-shadow: none !important;
            width: auto !important;
        }

        div[data-testid="stMultiSelect"] input {
            background: transparent !important;
            color: #f5f5f7 !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            padding: 0 4px !important;
        }

        div[data-baseweb="select"] input {
            box-shadow: none !important;
            background: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Konstanta & Konfigurasi
TYPE_CONFIG = {
    "Video": {"bg": "rgba(255, 69, 58, 0.18)", "border": "#ff453a", "text": "#ff857a", "label": "Video"},
    "Poster": {"bg": "rgba(255, 214, 10, 0.18)", "border": "#ffd60a", "text": "#ffec80", "label": "Poster"},
    "Campaign Poster": {"bg": "rgba(10, 132, 255, 0.18)", "border": "#0a84ff", "text": "#80bfff", "label": "Campaign"}
}
COLUMNS_STATUS = ["Ideation", "Shooting", "Editing", "Done"]
AVAILABLE_PLATFORMS = ["TikTok", "Instagram Reels", "YouTube", "Banner / Print", "Instagram Feed", "Commercial Ad"]
AVAILABLE_TYPES = ["Video", "Poster", "Campaign Poster"]
NAV_OPTIONS = ["Home", "Kanban Board", "Calendar", "Create Task", "Analytics"]

all_tasks = db.fetch_tasks()
today = date.today()
today_str = today.isoformat()
tomorrow = today + timedelta(days=1)
tomorrow_str = tomorrow.isoformat()

HARI_MAP = {
    "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
    "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
}
BULAN_MAP = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

def format_id_date(d):
    h = HARI_MAP.get(d.strftime("%A"), d.strftime("%A"))
    b = BULAN_MAP.get(d.month, d.strftime("%B"))
    return f"{h}, {d.day:02d} {b} {d.year}"

def parse_platforms(plat_val):
    if not plat_val:
        return []
    return [p.strip() for p in plat_val.split(",") if p.strip()]

def format_platform_display(plat_val):
    platforms = parse_platforms(plat_val)
    if not platforms:
        return "-"
    if len(platforms) == 1:
        return platforms[0]
    return f"{platforms[0]} +{len(platforms)-1}"

today_display = format_id_date(today)
tomorrow_display = format_id_date(tomorrow)

# 4. Modal Dialog Workspace (Menggunakan form agar stabil tanpa mental saat diketik/upload)
def _open_task_dialog(task_id):
    """Callback on_click: set active_task_id sebelum script body berjalan.
    Ini memastikan autorefresh tidak di-mount saat dialog aktif."""
    st.session_state.active_task_id = task_id

@st.dialog("Task Workspace")
def task_detail_modal(task_id):
    st.session_state["_dialog_seen"] = True  # Tandai dialog sedang aktif (untuk deteksi X close)
    task = db.fetch_task_by_id(task_id)
    
    if not task:
        st.error("Task tidak ditemukan.")
        return

    c_left, c_right = st.columns([1.2, 1], gap="medium")

    with c_left:
        st.markdown(f"### {task['title']}")
        desc = st.text_area("Catatan Brief", value=task.get("description") or "", placeholder="Hook, script angle, catatan revisi...", height=120, key=f"d_desc_{task['id']}")

        if task.get("video_path") and os.path.exists(task["video_path"]):
            st.video(task["video_path"])
            if st.button("Hapus Video Draft", key=f"d_del_v_{task['id']}"):
                try:
                    os.remove(task["video_path"])
                except:
                    pass
                db.update_media_path(task['id'], "video_path", "")
                st.session_state.keep_dialog_open = True
                st.rerun()

        if task.get("thumbnail_path") and os.path.exists(task["thumbnail_path"]):
            st.image(task["thumbnail_path"], use_container_width=True)
            if st.button("Hapus Cover", key=f"d_del_i_{task['id']}"):
                try:
                    os.remove(task["thumbnail_path"])
                except:
                    pass
                db.update_media_path(task['id'], "thumbnail_path", "")
                st.session_state.keep_dialog_open = True
                st.rerun()

        with st.expander("Upload / Ganti Media"):
            up_vid = st.file_uploader("Upload Video Preview", type=["mp4", "mov"], key=f"d_up_v_{task['id']}_{st.session_state.upload_key}")
            if up_vid:
                v_ext = os.path.splitext(up_vid.name)[1]
                v_path = os.path.join(UPLOAD_DIR, f"v_{task['id']}_{int(datetime.now().timestamp())}{v_ext}")
                with open(v_path, "wb") as f:
                    f.write(up_vid.getbuffer())
                db.update_media_path(task['id'], "video_path", v_path)
                st.session_state.upload_key += 1  # Reset uploader agar tidak loop
                st.session_state.keep_dialog_open = True
                st.rerun()

            up_img = st.file_uploader("Upload Cover", type=["png", "jpg", "jpeg", "webp"], key=f"d_up_i_{task['id']}_{st.session_state.upload_key}")
            if up_img:
                i_ext = os.path.splitext(up_img.name)[1]
                i_path = os.path.join(UPLOAD_DIR, f"i_{task['id']}_{int(datetime.now().timestamp())}{i_ext}")
                with open(i_path, "wb") as f:
                    f.write(up_img.getbuffer())
                db.update_media_path(task['id'], "thumbnail_path", i_path)
                st.session_state.upload_key += 1  # Reset uploader agar tidak loop
                st.session_state.keep_dialog_open = True
                st.rerun()

    with c_right:
        st.markdown("**Parameter Brief:**")
        edit_title = st.text_input("Judul Konten", value=task["title"], key=f"d_tit_{task['id']}")
        edit_assignee = st.text_input("PIC / Editor", value=task["assignee"], key=f"d_ass_{task['id']}")
        
        try:
            curr_date = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        except:
            curr_date = today
        edit_deadline = st.date_input("Deadline", value=curr_date, key=f"d_dead_{task['id']}")

        edit_type = st.selectbox("Tipe", AVAILABLE_TYPES, index=AVAILABLE_TYPES.index(task.get("content_type", "Video")) if task.get("content_type") in AVAILABLE_TYPES else 0, key=f"d_typ_{task['id']}")

        existing_plats = parse_platforms(task.get("platform", ""))
        valid_defaults = [p for p in existing_plats if p in AVAILABLE_PLATFORMS]
        edit_platforms = st.multiselect("Platform Target", AVAILABLE_PLATFORMS, default=valid_defaults, key=f"d_plat_{task['id']}")

        edit_status = st.selectbox("Status", COLUMNS_STATUS, index=COLUMNS_STATUS.index(task["status"]) if task["status"] in COLUMNS_STATUS else 0, key=f"d_stat_{task['id']}")
        edit_asset_link = st.text_input("Link Cloud Storage", value=task.get("asset_link") or "", key=f"d_lnk_{task['id']}")

        st.write("")
        if st.button("💾 Simpan Perubahan", use_container_width=True, type="primary", key=f"d_save_{task['id']}"):
            platform_str = ", ".join(edit_platforms) if edit_platforms else "General"
            db.update_task_details(
                task["id"], edit_title, edit_assignee, str(edit_deadline),
                platform_str, edit_status, edit_type, edit_asset_link.strip(), desc.strip()
            )
            st.session_state.active_task_id = None
            st.session_state.success_msg = "Perubahan brief berhasil disimpan!"
            st.rerun()

        if st.button("🗑️ Hapus Task", use_container_width=True, key=f"d_del_{task['id']}"):
            db.delete_task(task["id"])
            st.session_state.active_task_id = None
            st.session_state.success_msg = "Task berhasil dihapus."
            st.rerun()

# Buka dialog setiap kali active_task_id di-set — baik dari klik tombol maupun rerun internal (upload/hapus media)
if st.session_state.get("active_task_id"):
    st.session_state.keep_dialog_open = False
    task_detail_modal(st.session_state.active_task_id)

# 5. Top Navbar Header
nav_left, nav_right = st.columns([1.0, 3.0], gap="medium")

with nav_left:
    st.markdown("""
        <div style='display: flex; align-items: center; gap: 12px; padding-top: 4px;'>
            <div style='background: linear-gradient(135deg, #ffd60a 0%, #f59e0b 100%); width: 34px; height: 34px; border-radius: 9px; display: flex; align-items: center; justify-content: center; font-weight: 900; color: #000000; font-size: 16px;'>⚡</div>
            <div>
                <div style='font-size: 15px; font-weight: 800; color: #f5f5f7; line-height: 1.1;'>Creative Dept</div>
                <div style='font-size: 11px; font-weight: 600; color: #86868b; margin-top: 1px;'>Honda Cengkareng • <span style='color: #34d399;'>● Synced</span></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with nav_right:
    current_idx = NAV_OPTIONS.index(st.session_state.current_nav) if st.session_state.current_nav in NAV_OPTIONS else 0
    try:
        menu = st.segmented_control(
            "Nav",
            NAV_OPTIONS,
            default=st.session_state.current_nav,
            label_visibility="collapsed"
        )
    except AttributeError:
        menu = st.radio(
            "Nav",
            NAV_OPTIONS,
            index=current_idx,
            horizontal=True,
            label_visibility="collapsed"
        )

if not menu:
    menu = "Home"

if menu != st.session_state.current_nav:
    st.session_state.current_nav = menu
    st.rerun()

st.markdown("<div style='height: 1px; background: rgba(255,255,255,0.08); margin: 16px 0 26px 0;'></div>", unsafe_allow_html=True)

# 6. Konten Halaman
if menu == "Home":
    h_top1, h_top2 = st.columns([1, 1])
    h_top1.markdown("<span style='font-size: 11px; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; color: #86868b;'>[ Creative Studio / 2026 ]</span>", unsafe_allow_html=True)
    h_top2.markdown("<div style='text-align: right; font-size: 11px; color: #ffd60a; letter-spacing: 1px; font-weight: 700;'>HONDA CENGKARENG MOTOR</div>", unsafe_allow_html=True)

    st.write("")

    c_img, c_text = st.columns([1.6, 2], gap="large")
    with c_img:
        img_target = "hero.png" if os.path.exists("hero.png") else ("hero.jpg" if os.path.exists("hero.jpg") else None)
        if img_target:
            st.image(img_target, use_container_width=True)
        else:
            st.warning("File hero.png atau hero.jpg belum ditemukan di folder project.")

    with c_text:
        st.markdown("<div style='font-size: 12px; color: #86868b; margin-bottom: 6px;'>[ Content Pipeline ]</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 42px; font-weight: 800; line-height: 1.1; letter-spacing: -1.5px; color: #f5f5f7; margin-bottom: 16px;'>Creative Department <br><span style='color: #ffd60a;'>of Honda Cengkareng.</span></div>", unsafe_allow_html=True)
        st.markdown("<p style='color: #a1a1a6; font-size: 15px; line-height: 1.6; max-width: 620px; margin-bottom: 24px;'>Ruang pusat kurasi brief, aset visual, draft video promo, dan automasi alur produksi konten harian secara tersentralisasi.</p>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 12px; color: #86868b;'>Sync Status: <strong style='color: #34d399;'>● Cloud Active</strong></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 1px; background: rgba(255,255,255,0.06); margin: 30px 0 24px 0;'></div>", unsafe_allow_html=True)

    today_tasks = [t for t in all_tasks if t["status"] != "Done" and t.get("deadline") == today_str]
    tomorrow_tasks = [t for t in all_tasks if t["status"] != "Done" and t.get("deadline") == tomorrow_str]

    col_today, col_tmrw = st.columns(2, gap="medium")

    with col_today:
        with st.container(border=True):
            th1, th2 = st.columns([2.2, 1])
            with th1:
                st.markdown(f"""
                    <div>
                        <div style='font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #ffd60a; margin-bottom: 2px;'>● HARI INI</div>
                        <div style='font-size: 17px; font-weight: 800; letter-spacing: -0.4px; color: #f5f5f7;'>{today_display}</div>
                    </div>
                """, unsafe_allow_html=True)
            with th2:
                st.markdown(f"""
                    <div style='text-align: right; padding-top: 4px;'>
                        <span style='background: rgba(255,214,10,0.12); border: 1px solid rgba(255,214,10,0.3); padding: 4px 10px; border-radius: 16px; font-size: 11px; font-weight: 700; color: #ffd60a;'>
                            {len(today_tasks)} Task
                        </span>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            if today_tasks:
                for t in today_tasks:
                    c_type = t.get("content_type", "Video")
                    c_conf = TYPE_CONFIG.get(c_type, TYPE_CONFIG["Video"])

                    st.button(f"📌 {t['title']}", key=f"tod_btn_{t['id']}", use_container_width=True, on_click=_open_task_dialog, args=(t["id"],))
                    
                    st.markdown(f"""
                        <div style='display: flex; justify-content: space-between; align-items: center; padding: 0 4px; margin-top: -6px; margin-bottom: 10px;'>
                            <span style='background: {c_conf['bg']}; color: {c_conf['text']}; border: 1px solid {c_conf['border']}; font-size: 10px; padding: 1px 7px; border-radius: 5px; font-weight: 700;'>{c_type}</span>
                            <span style='font-size: 11.5px; color: #86868b;'>{t['assignee']} • <strong style='color:#f5f5f7;'>{t['status']}</strong></span>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style='background: rgba(28, 28, 30, 0.25); border: 1px solid rgba(255,255,255,0.04); border-radius: 10px; padding: 16px; text-align: center; color: #86868b; font-size: 12.5px;'>
                        Tidak ada jadwal produksi untuk hari ini.
                    </div>
                """, unsafe_allow_html=True)

    with col_tmrw:
        with st.container(border=True):
            tm1, tm2 = st.columns([2.2, 1])
            with tm1:
                st.markdown(f"""
                    <div>
                        <div style='font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #0a84ff; margin-bottom: 2px;'>● BESOK</div>
                        <div style='font-size: 17px; font-weight: 800; letter-spacing: -0.4px; color: #f5f5f7;'>{tomorrow_display}</div>
                    </div>
                """, unsafe_allow_html=True)
            with tm2:
                st.markdown(f"""
                    <div style='text-align: right; padding-top: 4px;'>
                        <span style='background: rgba(10,132,255,0.12); border: 1px solid rgba(10,132,255,0.3); padding: 4px 10px; border-radius: 16px; font-size: 11px; font-weight: 700; color: #80bfff;'>
                            {len(tomorrow_tasks)} Task
                        </span>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            if tomorrow_tasks:
                for t in tomorrow_tasks:
                    c_type = t.get("content_type", "Video")
                    c_conf = TYPE_CONFIG.get(c_type, TYPE_CONFIG["Video"])

                    st.button(f"📌 {t['title']}", key=f"tmrw_btn_{t['id']}", use_container_width=True, on_click=_open_task_dialog, args=(t["id"],))
                    
                    st.markdown(f"""
                        <div style='display: flex; justify-content: space-between; align-items: center; padding: 0 4px; margin-top: -6px; margin-bottom: 10px;'>
                            <span style='background: {c_conf['bg']}; color: {c_conf['text']}; border: 1px solid {c_conf['border']}; font-size: 10px; padding: 1px 7px; border-radius: 5px; font-weight: 700;'>{c_type}</span>
                            <span style='font-size: 11.5px; color: #86868b;'>{t['assignee']} • <strong style='color:#f5f5f7;'>{t['status']}</strong></span>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style='background: rgba(28, 28, 30, 0.25); border: 1px solid rgba(255,255,255,0.04); border-radius: 10px; padding: 16px; text-align: center; color: #86868b; font-size: 12.5px;'>
                        Tidak ada jadwal produksi untuk besok.
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1px; background: rgba(255,255,255,0.06); margin: 26px 0 28px 0;'></div>", unsafe_allow_html=True)

    col_a, col_b = st.columns([2, 1], gap="large")
    with col_a:
        st.markdown("<div style='font-size: 12px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: #86868b; margin-bottom: 12px;'>● Jadwal Perlu Perhatian</div>", unsafe_allow_html=True)
        urgent_tasks = [t for t in all_tasks if t["status"] != "Done" and t.get("deadline") and t["deadline"] <= today_str]
        
        if urgent_tasks:
            for t in urgent_tasks:
                c_type = t.get("content_type", "Video")
                c_conf = TYPE_CONFIG.get(c_type, TYPE_CONFIG["Video"])
                st.markdown(f"""
                    <div style='background: rgba(24, 24, 26, 0.7); border-left: 4px solid #ff453a; border-top: 1px solid rgba(255,255,255,0.06); border-right: 1px solid rgba(255,255,255,0.06); border-bottom: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;'>
                        <div style='display: flex; align-items: center; gap: 12px;'>
                            <span style='background: {c_conf['bg']}; color: {c_conf['text']}; border: 1px solid {c_conf['border']}; font-size: 10px; padding: 3px 8px; border-radius: 6px; font-weight: 700;'>{c_type}</span>
                            <strong style='color: #f5f5f7; font-size: 14px;'>{t['title']}</strong>
                        </div>
                        <span style='color: #ff453a; font-size: 12px; font-weight: 600;'>{t['deadline']}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style='background: rgba(28, 28, 30, 0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 20px; text-align: center; color: #86868b; font-size: 13px;'>
                    Semua jadwal brief aman dan terkendali.
                </div>
            """, unsafe_allow_html=True)

    with col_b:
        st.markdown("<div style='font-size: 12px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: #86868b; margin-bottom: 12px;'>● Format Produksi</div>", unsafe_allow_html=True)
        for k, v in TYPE_CONFIG.items():
            with st.container(border=True):
                c_lbl, c_bdg = st.columns([3, 1])
                c_lbl.markdown(f"<span style='font-size: 13.5px; font-weight: 600;'>{k}</span>", unsafe_allow_html=True)
                c_bdg.markdown(f"<span style='background:{v['bg']}; color:{v['text']}; border:1px solid {v['border']}; font-size:10px; padding:3px 8px; border-radius:6px; font-weight:700;'>{v['label']}</span>", unsafe_allow_html=True)

elif menu == "Kanban Board":
    st.markdown("<h1 style='font-size: 32px; font-weight: 700; letter-spacing: -0.8px; margin-bottom: 2px;'>Kanban Board</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #86868b; font-size: 14px; margin-bottom: 20px;'>Pantau dan perbarui tahap pengerjaan setiap konten secara visual.</p>", unsafe_allow_html=True)

    available_assignees = sorted(list(set(t["assignee"] for t in all_tasks if t.get("assignee"))))
    f_col1, f_col2, f_col3, f_col4 = st.columns([1.2, 1.2, 0.8, 0.9], gap="medium")
    selected_types = f_col1.multiselect("Tipe Format", AVAILABLE_TYPES, default=[], placeholder="Semua Format Konten")
    selected_assignees = f_col2.multiselect("PIC / Editor", available_assignees, default=[], placeholder="Semua PIC")
    
    year_list = list(range(today.year, today.year + 11))
    year_options = [0] + year_list
    selected_year_filter = f_col3.selectbox(
        "Tahun",
        options=year_options,
        index=year_options.index(today.year),
        format_func=lambda x: "Semua Tahun" if x == 0 else str(x)
    )
    
    month_options = [0] + list(range(1, 13))
    selected_month_filter = f_col4.selectbox(
        "Bulan",
        options=month_options,
        index=today.month,
        format_func=lambda x: "Semua Bulan" if x == 0 else BULAN_MAP[x]
    )

    filtered_tasks = []
    for t in all_tasks:
        if selected_types and t.get("content_type", "Video") not in selected_types:
            continue
        if selected_assignees and t["assignee"] not in selected_assignees:
            continue
        if selected_year_filter != 0 or selected_month_filter != 0:
            if t.get("deadline"):
                try:
                    task_dt = datetime.strptime(t["deadline"], "%Y-%m-%d")
                    if selected_year_filter != 0 and task_dt.year != selected_year_filter:
                        continue
                    if selected_month_filter != 0 and task_dt.month != selected_month_filter:
                        continue
                except:
                    continue
            else:
                continue
        filtered_tasks.append(t)

    st.write("")
    cols = st.columns(len(COLUMNS_STATUS))

    for idx, col_name in enumerate(COLUMNS_STATUS):
        with cols[idx]:
            col_tasks = [t for t in filtered_tasks if t["status"] == col_name]
            
            with st.container(border=True):
                c_col_h, c_col_cnt = st.columns([3, 1])
                c_col_h.markdown(f"**{col_name}**")
                c_col_cnt.markdown(f"<span style='opacity:0.7; font-size:12px; font-weight:600;'>{len(col_tasks)}</span>", unsafe_allow_html=True)

            for task in col_tasks:
                c_type = task.get("content_type", "Video")
                c_conf = TYPE_CONFIG.get(c_type, TYPE_CONFIG["Video"])
                is_overdue = (task["status"] != "Done") and bool(task.get("deadline")) and (task["deadline"] < today_str)
                plat_display = format_platform_display(task.get("platform", ""))

                with st.container(border=True):
                    st.markdown(f"""
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
                            <span style='background: {c_conf['bg']}; color: {c_conf['text']}; border: 1px solid {c_conf['border']}; font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 6px;'>
                                {c_conf['label']}
                            </span>
                            <span style='font-size: 11.5px; opacity: 0.75; font-weight: 500;' title='{task.get("platform", "")}'>{plat_display}</span>
                        </div>
                    """, unsafe_allow_html=True)

                    if task.get("thumbnail_path") and os.path.exists(task["thumbnail_path"]):
                        st.image(task["thumbnail_path"], use_container_width=True)

                    st.button(f"📌 {task['title']}", key=f"open_{task['id']}", use_container_width=True, on_click=_open_task_dialog, args=(task["id"],))

                    st.caption(f"👤 {task['assignee']} • 📅 {task['deadline']}")
                    
                    if is_overdue:
                        st.markdown("<div style='font-size: 11px; margin-bottom: 8px;'><span style='color:#ff453a; font-weight:600;'>⚠️ Overdue</span></div>", unsafe_allow_html=True)

                    new_st = st.selectbox("Status", COLUMNS_STATUS, index=COLUMNS_STATUS.index(task['status']), key=f"st_{task['id']}", label_visibility="collapsed")
                    if new_st != task['status']:
                        db.update_status(task['id'], new_st)
                        st.rerun()

elif menu == "Calendar":
    st.markdown("<h1 style='font-size: 32px; font-weight: 700; letter-spacing: -0.8px; margin-bottom: 2px;'>Calendar</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #86868b; font-size: 14px; margin-bottom: 20px;'>Jadwal tenggat waktu dan agenda posting harian.</p>", unsafe_allow_html=True)

    available_assignees = sorted(list(set(t["assignee"] for t in all_tasks if t.get("assignee"))))
    cf1, cf2, cf3, cf4 = st.columns([1.2, 1.2, 0.8, 0.9], gap="medium")
    cal_selected_types = cf1.multiselect("Tipe Format", AVAILABLE_TYPES, default=[], placeholder="Semua Format Konten", key="c_type_f")
    cal_selected_assignees = cf2.multiselect("PIC / Editor", available_assignees, default=[], placeholder="Semua PIC", key="c_pic_f")

    current_year = today.year
    cal_year_options = list(range(current_year, current_year + 11))
    selected_year = cf3.selectbox("Tahun", options=cal_year_options, index=0, key="c_year_s")
    selected_month_num = cf4.selectbox("Bulan", options=list(range(1, 13)), format_func=lambda x: BULAN_MAP[x], index=today.month - 1, key="c_mo_s")

    cal_tasks = []
    for t in all_tasks:
        if cal_selected_types and t.get("content_type", "Video") not in cal_selected_types:
            continue
        if cal_selected_assignees and t["assignee"] not in cal_selected_assignees:
            continue
        cal_tasks.append(t)

    cal = calendar.monthcalendar(selected_year, selected_month_num)
    week_days = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]

    with st.container(border=True):
        cal_h1, cal_h2 = st.columns([2, 1])
        with cal_h1:
            st.markdown(f"<div style='font-size:12px; font-weight:800; letter-spacing:1.5px; text-transform:uppercase; color:#86868b;'>{BULAN_MAP[selected_month_num].upper()} {selected_year}</div>", unsafe_allow_html=True)
        with cal_h2:
            st.markdown("<div style='text-align:right; font-size:11px; color:#86868b;'><span style='color:#ff453a; font-size:14px;'>●</span> Ada Task Terjadwal</div>", unsafe_allow_html=True)

        st.write("")
        header_cols = st.columns(7)
        for i, h in enumerate(week_days):
            header_cols[i].markdown(f"<div style='text-align:center; font-size:12.5px; font-weight:700; color:#86868b;'>{h}</div>", unsafe_allow_html=True)

        for week in cal:
            day_cols = st.columns(7)
            for d_idx, day in enumerate(week):
                with day_cols[d_idx]:
                    if day == 0:
                        st.markdown("<div style='height:50px;'></div>", unsafe_allow_html=True)
                    else:
                        day_str = f"{selected_year:04d}-{selected_month_num:02d}-{day:02d}"
                        day_tasks = [t for t in cal_tasks if t.get("deadline") == day_str]
                        has_task = len(day_tasks) > 0
                        is_selected = (day_str == st.session_state.selected_cal_date)

                        btn_label = f"{day}  •" if has_task else str(day)
                        btn_kind = "primary" if is_selected else "secondary"

                        if st.button(btn_label, key=f"cal_page_{day_str}", use_container_width=True, type=btn_kind):
                            st.session_state.selected_cal_date = day_str
                            st.rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    try:
        sel_dt = datetime.strptime(st.session_state.selected_cal_date, "%Y-%m-%d").date()
        sel_display_date = format_id_date(sel_dt)
    except:
        sel_display_date = st.session_state.selected_cal_date

    tasks_on_selected_date = [t for t in cal_tasks if t.get("deadline") == st.session_state.selected_cal_date]

    st.markdown(f"<div style='font-size:12px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#86868b; margin-bottom:8px;'>● AGENDA TERJADWAL: {sel_display_date}</div>", unsafe_allow_html=True)

    if tasks_on_selected_date:
        for task in tasks_on_selected_date:
            c_type = task.get("content_type", "Video")
            c_conf = TYPE_CONFIG.get(c_type, TYPE_CONFIG["Video"])
            initial = (task["assignee"][:1] if task.get("assignee") else "U").upper()
            plat_display = format_platform_display(task.get("platform", ""))

            with st.container(border=True):
                card_c1, card_c2 = st.columns([4, 1.2], gap="small")
                with card_c1:
                    st.markdown(f"""
                        <div style='display: flex; align-items: center; gap: 14px; margin-bottom: 8px;'>
                            <div style='width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #f59e0b 0%, #ffd60a 100%); color: #000; font-weight: 800; font-size: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;'>
                                {initial}
                            </div>
                            <div>
                                <div style='font-size: 14px; font-weight: 700; color: #f5f5f7;'>{task['assignee']}</div>
                                <div style='font-size: 12px; color: #86868b;'>Status: <strong style='color:#f5f5f7;'>{task['status']}</strong> • Platform: <span title='{task.get("platform", "")}'>{plat_display}</span></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.button(f"📌 {task['title']}", key=f"cal_card_{task['id']}", use_container_width=True, on_click=_open_task_dialog, args=(task["id"],))

                with card_c2:
                    st.markdown(f"""
                        <div style='text-align: right; padding-top: 8px;'>
                            <span style='background: {c_conf['bg']}; color: {c_conf['text']}; border: 1px solid {c_conf['border']}; font-size: 11px; padding: 4px 10px; border-radius: 8px; font-weight: 700;'>
                                {c_type}
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style='background: rgba(28, 28, 30, 0.35); border: 1px dashed rgba(255,255,255,0.08); border-radius: 12px; padding: 22px; text-align: center; color: #86868b; font-size: 13.5px;'>
                Tidak ada jadwal brief atau posting untuk tanggal ini ({sel_display_date}).
            </div>
        """, unsafe_allow_html=True)

elif menu == "Create Task":
    st.markdown("<h1 style='font-size: 32px; font-weight: 700; letter-spacing: -0.8px; margin-bottom: 2px;'>Create Task</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #86868b; font-size: 14px; margin-bottom: 20px;'>Input brief konten baru untuk tim kreatif.</p>", unsafe_allow_html=True)

    with st.container(border=True):
        with st.form("new_content_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            title = col1.text_input("Judul Konten / Konsep *", placeholder="Misal: Review Oli Gardan Honda")
            assignee = col2.text_input("PIC / Editor / Designer *", placeholder="Nama penanggung jawab")
            
            col3, col4, col5, col6 = st.columns(4)
            deadline = col3.date_input("Deadline", today)
            content_type = col4.selectbox("Tipe Konten", AVAILABLE_TYPES)
            platforms = col5.multiselect("Platform Target", AVAILABLE_PLATFORMS, default=["TikTok"], placeholder="Pilih platform...")
            status = col6.selectbox("Status Awal", COLUMNS_STATUS)

            description = st.text_area("Deskripsi / Catatan Brief", placeholder="Tuliskan catatan hook, revisi, atau referensi angle...")
            asset_link = st.text_input("Link Cloud Storage (Drive / NAS)", placeholder="https://drive.google.com/...")

            submitted = st.form_submit_button("Simpan Brief Konten", use_container_width=True)
            if submitted:
                if title and assignee:
                    platform_str = ", ".join(platforms) if platforms else "General"
                    db.add_task(title, assignee, str(deadline), platform_str, status, asset_link.strip(), {}, content_type, description.strip())
                    st.session_state.success_msg = f"Task '{title}' berhasil dibuat!"
                    st.rerun()
                else:
                    st.error("Mohon lengkapi Judul dan PIC.")

elif menu == "Analytics":
    st.markdown("<h1 style='font-size: 32px; font-weight: 700; letter-spacing: -0.8px; margin-bottom: 2px;'>Analytics</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #86868b; font-size: 14px; margin-bottom: 20px;'>Performa dan output produksi konten.</p>", unsafe_allow_html=True)

    total_tasks = len(all_tasks)
    active_tasks = [t for t in all_tasks if t["status"] != "Done"]
    done_tasks = [t for t in all_tasks if t["status"] == "Done"]
    overdue_tasks = [t for t in active_tasks if t.get("deadline") and t["deadline"] < today_str]
    completion_rate = (len(done_tasks) / total_tasks * 100) if total_tasks > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Konten", total_tasks)
    k2.metric("Sedang Berjalan", len(active_tasks))
    k3.metric("Overdue", len(overdue_tasks), delta=f"-{len(overdue_tasks)}" if overdue_tasks else "Aman", delta_color="inverse")
    k4.metric("Selesai (Done)", f"{len(done_tasks)} ({completion_rate:.0f}%)")

    st.write("")
    st.markdown("<h4 style='font-size: 16px; font-weight: 600; color: #86868b; margin-bottom: 10px;'>DISTRIBUSI FORMAT</h4>", unsafe_allow_html=True)
    c_vid = len([t for t in all_tasks if t.get("content_type") == "Video"])
    c_pos = len([t for t in all_tasks if t.get("content_type") == "Poster"])
    c_cam = len([t for t in all_tasks if t.get("content_type") == "Campaign Poster"])

    ck1, ck2, ck3 = st.columns(3)
    ck1.metric("Video Production", c_vid)
    ck2.metric("Poster Single", c_pos)
    ck3.metric("Campaign Poster", c_cam)

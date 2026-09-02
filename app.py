import streamlit as st
import json
import os
import calendar
from datetime import date, datetime
from streamlit_autorefresh import st_autorefresh
import database as db

# 1. Inisialisasi & Setup Halaman
st.set_page_config(page_title="Content Production Hub", layout="wide", initial_sidebar_state="expanded")

if "modal_open" not in st.session_state:
    st.session_state.modal_open = False

if not st.session_state.modal_open:
    st_autorefresh(interval=4000, key="apple_glass_autorefresh")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
db.init_and_migrate_db()

# 2. Muat Styling Eksternal
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 3. Konstanta & Konfigurasi
TYPE_CONFIG = {
    "Video": {"bg": "rgba(255, 69, 58, 0.18)", "border": "#ff453a", "text": "#ff857a", "label": "Video"},
    "Poster": {"bg": "rgba(255, 214, 10, 0.18)", "border": "#ffd60a", "text": "#ffec80", "label": "Poster"},
    "Campaign Poster": {"bg": "rgba(10, 132, 255, 0.18)", "border": "#0a84ff", "text": "#80bfff", "label": "Campaign"}
}
COLUMNS_STATUS = ["Ideation", "Shooting", "Editing", "Done"]
AVAILABLE_PLATFORMS = ["TikTok", "Instagram Reels", "YouTube", "Banner / Print", "Instagram Feed", "Commercial Ad"]
AVAILABLE_TYPES = ["Video", "Poster", "Campaign Poster"]

all_tasks = db.fetch_tasks()
today = date.today()
today_str = today.isoformat()

# 4. Modal Dialog Workspace
@st.dialog("Task Workspace")
def task_detail_modal(task_id):
    st.session_state.modal_open = True
    task = db.fetch_task_by_id(task_id)
    
    if not task:
        st.error("Task tidak ditemukan.")
        st.session_state.modal_open = False
        return

    c_left, c_right = st.columns([1.2, 1], gap="medium")

    with c_left:
        st.markdown(f"### {task['title']}")
        desc = st.text_area("Catatan Brief", value=task.get("description") or "", placeholder="Hook, script angle, catatan revisi...", height=75)

        if task.get("video_path") and os.path.exists(task["video_path"]):
            st.video(task["video_path"])
            if st.button("Hapus Video Draft", key=f"m_del_v_{task['id']}"):
                os.remove(task["video_path"])
                db.update_media_path(task['id'], "video_path", "")
                st.rerun()

        if task.get("thumbnail_path") and os.path.exists(task["thumbnail_path"]):
            st.image(task["thumbnail_path"], use_container_width=True)
            if st.button("Hapus Cover", key=f"m_del_i_{task['id']}"):
                os.remove(task["thumbnail_path"])
                db.update_media_path(task['id'], "thumbnail_path", "")
                st.rerun()

        with st.expander("Upload / Ganti Media"):
            up_vid = st.file_uploader("Upload Video Preview", type=["mp4", "mov"], key=f"m_up_v_{task['id']}")
            if up_vid:
                v_ext = os.path.splitext(up_vid.name)[1]
                v_path = os.path.join(UPLOAD_DIR, f"v_{task['id']}_{int(datetime.now().timestamp())}{v_ext}")
                with open(v_path, "wb") as f:
                    f.write(up_vid.getbuffer())
                db.update_media_path(task['id'], "video_path", v_path)
                st.rerun()

            up_img = st.file_uploader("Upload Cover", type=["png", "jpg", "jpeg", "webp"], key=f"m_up_i_{task['id']}")
            if up_img:
                i_ext = os.path.splitext(up_img.name)[1]
                i_path = os.path.join(UPLOAD_DIR, f"i_{task['id']}_{int(datetime.now().timestamp())}{i_ext}")
                with open(i_path, "wb") as f:
                    f.write(up_img.getbuffer())
                db.update_media_path(task['id'], "thumbnail_path", i_path)
                st.rerun()

        st.markdown("**Checklist Output:**")
        raw_chk = task.get("checklist") or "{}"
        try:
            chk_data = json.loads(raw_chk) if isinstance(raw_chk, str) else raw_chk
        except:
            chk_data = {}

        standard_items = ["Raw Footage / Assets", "Voiceover / Audio", "Color Grading / Retouch", "Typography / Copy", "Final Export / Render"]
        for item in standard_items:
            if item not in chk_data:
                chk_data[item] = False

        changed_chk = False
        col_chk1, col_chk2 = st.columns(2)
        for i, item in enumerate(standard_items):
            target_col = col_chk1 if i % 2 == 0 else col_chk2
            checked = target_col.checkbox(item, value=chk_data.get(item, False), key=f"m_chk_{task['id']}_{item}")
            if checked != chk_data.get(item, False):
                chk_data[item] = checked
                changed_chk = True
        if changed_chk:
            db.update_checklist(task['id'], chk_data)
            st.rerun()

    with c_right:
        st.markdown("**Parameter Brief:**")
        edit_title = st.text_input("Judul Konten", value=task["title"])
        edit_assignee = st.text_input("PIC / Editor", value=task["assignee"])
        
        try:
            curr_date = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
        except:
            curr_date = today
        edit_deadline = st.date_input("Deadline", value=curr_date)

        edit_type = st.selectbox("Tipe", AVAILABLE_TYPES, index=AVAILABLE_TYPES.index(task.get("content_type", "Video")) if task.get("content_type") in AVAILABLE_TYPES else 0)
        edit_platform = st.selectbox("Platform", AVAILABLE_PLATFORMS, index=AVAILABLE_PLATFORMS.index(task["platform"]) if task["platform"] in AVAILABLE_PLATFORMS else 0)
        edit_status = st.selectbox("Status", COLUMNS_STATUS, index=COLUMNS_STATUS.index(task["status"]) if task["status"] in COLUMNS_STATUS else 0)
        edit_asset_link = st.text_input("Link Cloud Storage", value=task.get("asset_link") or "")

        st.write("")
        if st.button("💾 Simpan Perubahan", use_container_width=True, type="primary"):
            db.update_task_details(
                task["id"], edit_title, edit_assignee, str(edit_deadline),
                edit_platform, edit_status, edit_type, edit_asset_link.strip(), desc.strip()
            )
            st.session_state.modal_open = False
            st.toast("Perubahan tersimpan!", icon="✅")
            st.rerun()

        if st.button("🗑️ Hapus Task", use_container_width=True):
            db.delete_task(task["id"])
            st.session_state.modal_open = False
            st.rerun()

# 5. Sidebar Navigation
with st.sidebar:
    st.markdown("""
        <div style='background: linear-gradient(135deg, #ffd60a 0%, #f59e0b 100%); padding: 12px 14px; border-radius: 14px; margin-bottom: 24px; box-shadow: 0 8px 20px rgba(255, 214, 10, 0.2);'>
            <div style='font-size: 13px; font-weight: 800; color: #000000; line-height: 1.2;'>Creative Dept</div>
            <div style='font-size: 11px; font-weight: 600; color: rgba(0,0,0,0.7); margin-top: 2px;'>Honda Cengkareng</div>
        </div>
    """, unsafe_allow_html=True)

    menu = st.radio("Navigation", ["Home", "Production Board", "Create Task", "Analytics"], label_visibility="collapsed")
    st.markdown("<div style='height: 1px; background: rgba(255,255,255,0.08); margin: 24px 0 16px 0;'></div>", unsafe_allow_html=True)
    
    st.markdown("""
        <div style='padding: 10px 12px; background: rgba(255,255,255,0.03); border-radius: 10px; border: 1px solid rgba(255,255,255,0.06);'>
            <div style='font-size: 11px; color: #86868b;'>Live Hub</div>
            <div style='font-size: 12px; font-weight: 600; color: #34d399; margin-top: 2px;'>● Real-time Synced</div>
        </div>
    """, unsafe_allow_html=True)

# 6. Konten Halaman
if menu == "Home":
    st.markdown("<h1 style='font-size: 32px; font-weight: 700; letter-spacing: -0.8px; margin-bottom: 2px;'>Welcome</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #86868b; font-size: 14px; margin-bottom: 20px;'>{today.strftime('%A, %d %B %Y')}</p>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        with st.container(border=True):
            st.markdown("#### ⚡ Honda Cengkareng Content Production")
            st.write("Semua pembaruan thumbnail, draft video player, dan status brief tersinkronisasi otomatis via Cloudflare Tunnel.")
        
        st.markdown("<h4 style='font-size: 16px; font-weight: 600; color: #86868b; margin: 18px 0 10px 0;'>PERLU PERHATIAN</h4>", unsafe_allow_html=True)
        urgent_tasks = [t for t in all_tasks if t["status"] != "Done" and t.get("deadline") and t["deadline"] <= today_str]
        if urgent_tasks:
            for t in urgent_tasks:
                c_type = t.get("content_type", "Video")
                c_conf = TYPE_CONFIG.get(c_type, TYPE_CONFIG["Video"])
                st.markdown(f"""
                    <div style='background: rgba(28, 28, 30, 0.65); border-left: 4px solid #ff453a; border-top: 1px solid rgba(255,255,255,0.06); border-right: 1px solid rgba(255,255,255,0.06); border-bottom: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px 16px; margin-bottom: 10px;'>
                        <span style='background: {c_conf['bg']}; color: {c_conf['text']}; border: 1px solid {c_conf['border']}; font-size: 11px; padding: 2px 8px; border-radius: 6px; font-weight: 600;'>{c_type}</span>
                        <strong style='color: #f5f5f7; font-size: 14px; margin-left: 8px;'>{t['title']}</strong>
                        <span style='color: #ff453a; float: right; font-size: 12px; font-weight: 600;'>{t['deadline']}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.success("Semua jadwal konten berjalan tepat waktu.")

    with col_b:
        st.markdown("<h4 style='font-size: 16px; font-weight: 600; color: #86868b; margin-bottom: 10px;'>FORMAT KONTEN</h4>", unsafe_allow_html=True)
        for k, v in TYPE_CONFIG.items():
            with st.container(border=True):
                c_lbl, c_bdg = st.columns([3, 1])
                c_lbl.markdown(f"**{k}**")
                c_bdg.markdown(f"<span style='background:{v['bg']}; color:{v['text']}; border:1px solid {v['border']}; font-size:11px; padding:3px 8px; border-radius:6px; font-weight:600;'>{v['label']}</span>", unsafe_allow_html=True)

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
            platform = col5.selectbox("Platform Target", AVAILABLE_PLATFORMS)
            status = col6.selectbox("Status Awal", COLUMNS_STATUS)

            description = st.text_area("Deskripsi / Catatan Brief", placeholder="Tuliskan catatan hook, revisi, atau referensi angle...")
            asset_link = st.text_input("Link Cloud Storage (Drive / NAS)", placeholder="https://drive.google.com/...")

            submitted = st.form_submit_button("Simpan Brief Konten", use_container_width=True)
            if submitted:
                if title and assignee:
                    default_checklist = {
                        "Raw Footage / Assets": False, "Voiceover / Audio": False,
                        "Color Grading / Retouch": False, "Typography / Copy": False, "Final Export / Render": False
                    }
                    db.add_task(title, assignee, str(deadline), platform, status, asset_link.strip(), default_checklist, content_type, description.strip())
                    st.toast("Brief berhasil disimpan!", icon="✨")
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

elif menu == "Production Board":
    st.markdown("<h1 style='font-size: 32px; font-weight: 700; letter-spacing: -0.8px; margin-bottom: 2px;'>Production Board</h1>", unsafe_allow_html=True)
    
    with st.expander("🔍 Filter & Mode Board"):
        f_col1, f_col2, f_col3 = st.columns([1, 1, 1])
        available_assignees = sorted(list(set(t["assignee"] for t in all_tasks if t.get("assignee"))))
        selected_types = f_col1.multiselect("Tipe Format", AVAILABLE_TYPES, default=[])
        selected_assignees = f_col2.multiselect("PIC / Editor", available_assignees, default=[])
        view_mode = f_col3.radio("Tampilan", ["Kanban Board", "Kalender Bulanan"], horizontal=True)

    filtered_tasks = []
    for t in all_tasks:
        if selected_types and t.get("content_type", "Video") not in selected_types:
            continue
        if selected_assignees and t["assignee"] not in selected_assignees:
            continue
        filtered_tasks.append(t)

    st.write("")

    if "Kanban Board" in view_mode:
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

                    raw_chk = task.get("checklist") or "{}"
                    try:
                        chk_data = json.loads(raw_chk) if isinstance(raw_chk, str) else raw_chk
                    except:
                        chk_data = {}
                    done_chk = sum(1 for v in chk_data.values() if v)
                    total_chk = len(chk_data) if len(chk_data) > 0 else 5

                    with st.container(border=True):
                        st.markdown(f"""
                            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
                                <span style='background: {c_conf['bg']}; color: {c_conf['text']}; border: 1px solid {c_conf['border']}; font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 6px;'>
                                    {c_conf['label']}
                                </span>
                                <span style='font-size: 12px; opacity: 0.7;'>{task['platform']}</span>
                            </div>
                        """, unsafe_allow_html=True)

                        if task.get("thumbnail_path") and os.path.exists(task["thumbnail_path"]):
                            st.image(task["thumbnail_path"], use_container_width=True)

                        if st.button(f"📌 {task['title']}", key=f"open_{task['id']}", use_container_width=True):
                            task_detail_modal(task["id"])

                        st.caption(f"👤 {task['assignee']} • 📅 {task['deadline']}")
                        
                        st.markdown(f"""
                            <div style='display: flex; justify-content: space-between; font-size: 11px; opacity: 0.7; margin-bottom: 8px;'>
                                <span>📋 {done_chk}/{total_chk} checklist</span>
                                {f"<span style='color:#ff453a; font-weight:600;'>⚠️ Overdue</span>" if is_overdue else ""}
                            </div>
                        """, unsafe_allow_html=True)

                        new_st = st.selectbox("Status", COLUMNS_STATUS, index=COLUMNS_STATUS.index(task['status']), key=f"st_{task['id']}", label_visibility="collapsed")
                        if new_st != task['status']:
                            db.update_status(task['id'], new_st)
                            st.rerun()

    else:
        c_yr, c_mo = st.columns([1, 2])
        current_year = today.year
        current_month = today.month

        selected_year = c_yr.selectbox("Tahun", options=list(range(current_year - 1, current_year + 3)), index=1)
        selected_month_num = c_mo.selectbox("Bulan", options=list(range(1, 13)), format_func=lambda x: calendar.month_name[x], index=current_month - 1)

        cal = calendar.monthcalendar(selected_year, selected_month_num)
        week_days = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
        
        header_cols = st.columns(7)
        for i, h in enumerate(week_days):
            header_cols[i].markdown(f"<div style='text-align:center; font-size:13px; font-weight:600; opacity:0.6; padding-bottom:12px;'>{h}</div>", unsafe_allow_html=True)

        for week in cal:
            day_cols = st.columns(7)
            for d_idx, day in enumerate(week):
                with day_cols[d_idx]:
                    if day == 0:
                        st.markdown("<div style='height: 110px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 14px; margin-bottom: 8px;'></div>", unsafe_allow_html=True)
                    else:
                        day_str = f"{selected_year:04d}-{selected_month_num:02d}-{day:02d}"
                        day_tasks = [t for t in filtered_tasks if t.get("deadline") == day_str]
                        is_current_day = (day_str == today_str)

                        with st.container(border=True):
                            date_color = "#ffd60a" if is_current_day else "#f5f5f7"
                            st.markdown(f"<div style='font-size: 13px; font-weight: 700; color: {date_color}; text-align: right; margin-bottom: 2px;'>{day}</div>", unsafe_allow_html=True)
                            
                            for t in day_tasks:
                                c_type = t.get("content_type", "Video")
                                c_conf = TYPE_CONFIG.get(c_type, TYPE_CONFIG["Video"])
                                
                                st.markdown(f"""
                                    <style>
                                        button[key="cal_btn_{t['id']}"] {{
                                            background-color: {c_conf['bg']} !important;
                                            border: 1px solid {c_conf['border']} !important;
                                            color: {c_conf['text']} !important;
                                            border-radius: 6px !important;
                                            font-size: 11px !important;
                                            font-weight: 600 !important;
                                            padding: 3px 6px !important;
                                        }}
                                    </style>
                                """, unsafe_allow_html=True)
                                
                                if st.button(f"● {t['title']}", key=f"cal_btn_{t['id']}", use_container_width=True):
                                    task_detail_modal(t["id"])
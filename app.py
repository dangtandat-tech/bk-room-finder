import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import re

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="BK Room Finder", page_icon="🏫", layout="wide")

# --- 2. CSS (GIAO DIỆN MODERN LIGHT UI - ĐẸP & HIỆN ĐẠI) ---
st.markdown("""
<style>
    /* Container chính của thẻ */
    .room-card-container {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        overflow: hidden; /* Để nút bấm bên dưới cũng được bo góc */
        transition: all 0.3s ease;
        height: 100%; /* Để các thẻ trong cùng hàng cao bằng nhau */
        display: flex;
        flex-direction: column;
        border: 1px solid #f0f0f0;
    }
    .room-card-container:hover {
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        transform: translateY(-3px);
        border-color: #e0e0e0;
    }

    /* Phần nội dung HTML bên trên */
    .card-content {
        padding: 16px;
        flex-grow: 1; /* Chiếm phần lớn không gian để đẩy nút xuống đáy */
    }
    /* Các biến thể màu sắc cho viền trái */
    .border-free { border-left: 6px solid #28a745; }
    .border-soon { border-left: 6px solid #ffc107; }
    .border-busy { border-left: 6px solid #dc3545; }

    /* Header: Tên phòng + Badge */
    .card-header-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
    }
    .room-name-group {
        display: flex;
        align-items: center;
    }
    .room-icon { font-size: 1.4rem; margin-right: 8px; }
    .room-name {
        font-size: 1.3rem;
        font-weight: 800;
        color: #2c3e50;
    }
    /* Badge mã lớp */
    .code-badge {
        font-size: 0.75rem;
        background: #f1f3f5;
        color: #495057;
        padding: 4px 10px;
        border-radius: 20px; /* Bo tròn kiểu viên thuốc */
        font-weight: 700;
        white-space: nowrap;
        border: 1px solid #e9ecef;
    }

    /* Phần thông tin chi tiết (msg) */
    .room-detail-msg {
        font-size: 0.95rem;
        color: #666;
        line-height: 1.5;
    }
    .msg-main {
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 4px;
    }
    .msg-sub {
        font-size: 0.85rem;
        color: #888;
    }
    /* Màu text highlight */
    .text-free { color: #28a745; }
    .text-soon { color: #d9a406; } /* Màu vàng tối hơn chút để dễ đọc trên nền trắng */
    .text-busy { color: #dc3545; }

    /* Nút bấm Streamlit ở dưới (Phẳng & Liền mạch) */
    div.stButton > button {
        width: 100%;
        border-radius: 0; /* Bỏ bo góc riêng của nút */
        border: none;
        border-top: 1px solid #f0f0f0;
        background-color: #fcfcfc;
        color: #0d6efd;
        font-weight: 600;
        padding: 12px 0;
        margin: 0 !important; /* Reset margin để dính liền */
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #f0f2f5;
        color: #0a58ca;
    }
    
    /* Tinh chỉnh layout cột */
    div[data-testid="column"] { padding: 0 10px; margin-bottom: 20px; }

    /* Các phần khác giữ nguyên */
    .schedule-item {
        background: white; border-left: 5px solid #0d6efd;
        padding: 15px; margin-bottom: 12px; border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); color: #333;
    }
    .header-info {
        background-color: #fff; padding: 20px; border-radius: 12px;
        margin-bottom: 30px; border: 1px solid #e0e0e0; text-align: center; color: #333;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .header-info h3 { color: #d63384; font-weight: 800; letter-spacing: -0.5px; }
</style>
""", unsafe_allow_html=True)

START_DATE_K70 = datetime(2025, 9, 8)
TZ_VN = pytz.timezone('Asia/Ho_Chi_Minh')

# --- 3. HELPER FUNCTIONS ---
def parse_weeks(w_str):
    if pd.isna(w_str): return []
    res = []
    try:
        parts = str(w_str).replace('"', '').split(',')
        for p in parts:
            if '-' in p:
                s, e = map(int, p.split('-'))
                res.extend(range(s, e + 1))
            else:
                res.append(int(p))
    except: pass
    return res

def parse_time(t_str):
    if pd.isna(t_str) or '-' not in str(t_str): return None, None
    try:
        s, e = str(t_str).split('-')
        return s.strip().zfill(4), e.strip().zfill(4)
    except: return None, None

def check_week(w_str, current_week):
    return str(current_week) in str(w_str).split(',')

def clean_day(v):
    try: return str(int(float(v)))
    except: return str(v)

# --- 4. LOAD DATA ---
@st.cache_data
def load_and_process():
    files = ['data1.csv', 'data2.csv', 'TKB20251-K70.xlsx - Sheet1.csv', 'TKB20251-Full1.xlsx - Sheet1.csv']
    dfs = []
    encodings = ['utf-8-sig', 'utf-16', 'utf-8', 'cp1258', 'latin1']
    
    server_files = os.listdir()
    
    for f in files:
        if not os.path.exists(f):
            for sf in server_files:
                if sf.lower() == f.lower():
                    f = sf
                    break
            else: continue
            
        for enc in encodings:
            try:
                df_t = pd.read_csv(f, skiprows=2, encoding=enc, sep=None, engine='python', dtype=str)
                if df_t.shape[1] > 1:
                    df_t.columns = df_t.columns.str.strip().str.replace('\ufeff', '')
                    dfs.append(df_t)
                    break
            except: continue
    
    if not dfs: return pd.DataFrame()
    df_raw = pd.concat(dfs, ignore_index=True)

    cols = df_raw.columns.tolist()
    def fc(kws):
        for c in cols:
            for kw in kws: 
                if kw.lower() in c.lower(): return c
        return None
    
    c_room = fc(['phòng', 'phong'])
    c_time = fc(['thời_gian', 'time'])
    c_day  = fc(['thứ', 'thu', 'day'])
    c_week = fc(['tuần', 'tuan'])
    c_name = fc(['tên_hp', 'ten_hp', 'name'])
    c_code = fc(['mã_lớp', 'ma_lop', 'class_id'])

    if not c_room or not c_time: return pd.DataFrame()

    df = pd.DataFrame()
    df['MY_ROOM'] = df_raw[c_room]
    df['MY_TIME'] = df_raw[c_time]
    df['MY_DAY']  = df_raw[c_day] if c_day else "2"
    df['MY_WEEK'] = df_raw[c_week] if c_week else ""
    df['MY_NAME'] = df_raw[c_name] if c_name else "Lớp học"
    df['MY_CODE'] = df_raw[c_code] if c_code else ""

    df = df.dropna(subset=['MY_ROOM', 'MY_TIME'])
    df = df[df['MY_ROOM'] != 'NULL']

    tp = df['MY_TIME'].apply(parse_time)
    df['Start'] = tp.apply(lambda x: x[0])
    df['End'] = tp.apply(lambda x: x[1])
    df = df.dropna(subset=['Start', 'End'])

    df['Parsed_Weeks'] = df['MY_WEEK'].apply(lambda x: ",".join(map(str, parse_weeks(x))))

    def extract_building(room_name):
        s = str(room_name).strip()
        if '-' in s: return s.split('-')[0]
        return "Khác"
    df['Building'] = df['MY_ROOM'].apply(extract_building)
    
    return df

# --- 5. APP LOGIC ---
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'list'
if 'selected_room_data' not in st.session_state: st.session_state.selected_room_data = None
if 'current_time' not in st.session_state: st.session_state.current_time = datetime.now(TZ_VN)

st.title("🏫 Tra Cứu Phòng Trống BK")

try: df = load_and_process()
except Exception as e:
    st.error(f"Lỗi data: {e}")
    st.stop()

if df.empty:
    st.warning("Chưa tải được dữ liệu. Vui lòng kiểm tra file trên GitHub.")
    st.stop()

# Time Logic
now = st.session_state.current_time
now_naive = now.replace(tzinfo=None)
delta = now_naive - START_DATE_K70
curr_week = (delta.days // 7) + 1 if delta.days >= 0 else 0
py_to_bk = {0: '2', 1: '3', 2: '4', 3: '5', 4: '6', 5: '7', 6: '8'}
curr_wd = py_to_bk.get(now.weekday(), '2')

# --- MÀN HÌNH 1: LIST ---
if st.session_state.view_mode == 'list':
    st.sidebar.header("🔍 Bộ Lọc & Giao diện")
    num_cols = st.sidebar.slider("Số cột hiển thị", 1, 5, 3, key="num_cols_slider", help="Kéo để thay đổi kích thước thẻ")
    
    with st.sidebar.expander("🛠️ Chỉnh giờ"):
        if st.checkbox("Chỉnh tay", key="chk_manual"):
            d_v = st.date_input("Ngày", st.session_state.current_time, key="date_in")
            t_v = st.time_input("Giờ", st.session_state.current_time.time(), key="time_in")
            st.session_state.current_time = TZ_VN.localize(datetime.combine(d_v, t_v))
        else:
            if st.button("Cập nhật giờ", key="btn_update"):
                st.session_state.current_time = datetime.now(TZ_VN)
                st.rerun()

    buildings = sorted([b for b in df['Building'].unique() if b != 'Khác'])
    sel_b = st.sidebar.selectbox("📍 Chọn Tòa Nhà", buildings, key="sel_build")

    st.markdown(f"""
    <div class="header-info">
        <h3 style="margin:0">{now.strftime('%H:%M')} <span style="color:#333">|</span> Thứ {curr_wd} <span style="color:#333">|</span> {now.strftime('%d/%m/%Y')}</h3>
        <p style="margin:5px 0 0 0; font-size: 1.1rem">Tuần học: <b>{curr_week}</b></p>
    </div>
    """, unsafe_allow_html=True)

    df_b = df[df['Building'] == sel_b]
    df_today = df_b[df_b['MY_DAY'].apply(clean_day) == curr_wd]
    df_active = df_today[df_today['Parsed_Weeks'].apply(lambda x: check_week(x, curr_week))]

    def get_room_status(schedule, c_time_full):
        c_hm = c_time_full.hour * 60 + c_time_full.minute
        slots = []
        for _, row in schedule.iterrows():
            try:
                sh, sm = int(row['Start'][:2]), int(row['Start'][2:])
                eh, em = int(row['End'][:2]), int(row['End'][2:])
                slots.append({
                    'start_val': sh * 60 + sm, 'end_val': eh * 60 + em, 
                    'name': row['MY_NAME'], 'code': row['MY_CODE'], 
                    'end_str': f"{eh:02d}:{em:02d}", 'start_str': f"{sh:02d}:{sm:02d}"
                })
            except: continue
        slots.sort(key=lambda x: x['start_val'])
        
        for x in slots:
            if x['start_val'] <= c_hm <= x['end_val']:
                l = x['end_val'] - c_hm
                return "BUSY", f"ĐANG HỌC: {x['name']}<br>Đến: {x['end_str']} (Còn {l//60}h{l%60}p)", 3, x['code']
        
        for x in slots:
            if x['start_val'] > c_hm:
                diff = x['start_val'] - c_hm
                t_str = f"{diff//60}h{diff%60}p" if diff//60 > 0 else f"{diff%60}p"
                next_txt = f"Sau: {x['name']} ({x['start_str']})"
                if diff >= 45: return "FREE", f"TRỐNG: {t_str}<br>{next_txt}", 1, x['code']
                else: return "SOON", f"Sắp học trong {t_str}<br>{next_txt}", 2, x['code']
        
        return "FREE", "TRỐNG đến hết ngày hôm nay", 0, "NULL"

    rooms = sorted(df_b['MY_ROOM'].unique())
    results = []
    for r in rooms:
        r_sch = df_active[df_active['MY_ROOM'] == r]
        stt, msg, prio, code = get_room_status(r_sch, now)
        results.append({"r": r, "msg": msg, "st": stt, "prio": prio, "code": code})
    
    results.sort(key=lambda x: (x['prio'], x['r']))

    if not results:
        st.info("Không có dữ liệu phòng cho tòa nhà này hôm nay.")
    else:
        chunk_size = num_cols
        for i in range(0, len(results), chunk_size):
            cols = st.columns(chunk_size)
            row_items = results[i:i+chunk_size]
            
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    # 1. Xác định Class màu sắc và Icon
                    if item['st'] == 'FREE':
                        border_cls = "border-free"
                        text_cls = "text-free"
                        icon = "✅"
                    elif item['st'] == 'SOON':
                        border_cls = "border-soon"
                        text_cls = "text-soon"
                        icon = "⚠️"
                    else:
                        border_cls = "border-busy"
                        text_cls = "text-busy"
                        icon = "⛔"
                    
                    # 2. Xử lý Badge Mã lớp
                    code_text = item['code']
                    if str(code_text) == "NULL" or not code_text:
                        code_html = "" # Ẩn luôn nếu NULL cho gọn
                    else:
                        code_html = f'<span class="code-badge">{code_text}</span>'

                    # 3. Xử lý Message (Tách dòng chính/phụ để style đẹp hơn)
                    msg_parts = item['msg'].split('<br>')
                    main_msg = msg_parts[0]
                    sub_msg = msg_parts[1] if len(msg_parts) > 1 else ""

                    # 4. Render HTML Card (Cấu trúc mới)
                    st.markdown(f"""
                    <div class="room-card-container {border_cls}">
                        <div class="card-content">
                            <div class="card-header-row">
                                <div class="room-name-group">
                                    <span class="room-icon">{icon}</span>
                                    <span class="room-name">{item['r']}</span>
                                </div>
                                {code_html}
                            </div>
                            <div class="room-detail-msg">
                                <div class="msg-main {text_cls}">{main_msg}</div>
                                <div class="msg-sub">{sub_msg}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 5. Nút bấm (Đã được CSS để dính liền vào HTML trên)
                    if st.button("Xem lịch chi tiết", key=f"btn_{item['r']}_{idx}"):
                        st.session_state.selected_room_data = item['r']
                        st.session_state.view_mode = 'detail'
                        st.rerun()

# --- MÀN HÌNH 2: DETAIL ---
elif st.session_state.view_mode == 'detail':
    r_name = st.session_state.selected_room_data
    c1, c2 = st.columns([1, 6])
    with c1:
        st.markdown("<br>", unsafe_allow_html=True) # Căn chỉnh nút back
        if st.button("⬅️ Quay lại", key="btn_back"):
            st.session_state.view_mode = 'list'
            st.rerun()
    with c2:
        st.markdown(f"## 📅 Lịch học: <span style='color:#0d6efd'>{r_name}</span> (Tuần {curr_week})", unsafe_allow_html=True)
        
    df_week = df[
        (df['MY_ROOM'] == r_name) & 
        (df['Parsed_Weeks'].apply(lambda x: check_week(x, curr_week)))
    ].copy()
    
    st.divider()
    
    if df_week.empty:
        st.info("Phòng này không có lịch học trong tuần này.")
    else:
        df_week['Day_Sort'] = df_week['MY_DAY'].apply(lambda x: int(float(x)) if x else 0)
        df_week = df_week.sort_values(by=['Day_Sort', 'Start'])
        
        for _, row in df_week.iterrows():
            d = str(int(float(row['MY_DAY'])))
            st.markdown(f"""
            <div class="schedule-item">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span style="font-weight:bold; font-size:1.1rem">Thứ {d}</span>
                    <span style="font-weight:bold; color:#555">{row['Start'][:2]}:{row['Start'][2:]} - {row['End'][:2]}:{row['End'][2:]}</span>
                </div>
                <div style="color:#d63384; font-weight:700; font-size: 1.05rem; margin-bottom: 5px;">{row['MY_NAME']}</div>
                <div style="font-size:0.9rem; color:#666; display:flex; align-items:center;">
                    <span style="margin-right: 10px;">📌 Mã lớp: <b>{row['MY_CODE']}</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
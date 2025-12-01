import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="BK Room Finder", page_icon="🏫", layout="wide")

# --- 2. CSS (FINAL V30 - DARK MODE & CLEAN BUTTON) ---
st.markdown("""
<style>
    /* 1. CARD CONTAINER */
    .room-card-box {
        /* Dùng màu nền phụ của Streamlit: Tự động xám nhẹ ở Light Mode, xám tối ở Dark Mode */
        background-color: var(--secondary-background-color);
        border-radius: 10px;
        /* Viền mờ sử dụng rgba để hợp với mọi nền */
        border: 1px solid rgba(128, 128, 128, 0.2);
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 12px;
        overflow: hidden;
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    
    .room-card-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        border-color: rgba(13, 110, 253, 0.5); /* Viền xanh khi hover */
    }

    /* 2. DẢI MÀU TRẠNG THÁI (Viền trái đậm hơn chút) */
    .status-strip-free { border-left: 5px solid #28a745; }
    .status-strip-soon { border-left: 5px solid #ffc107; }
    .status-strip-busy { border-left: 5px solid #dc3545; }

    /* 3. NỘI DUNG CARD */
    .card-body {
        padding: 16px;
        flex-grow: 1;
    }

    /* Header: Tên phòng */
    .room-name {
        font-size: 1.3rem;
        font-weight: 800;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        /* Màu chữ tự động theo theme */
        color: var(--text-color); 
    }
    
    /* Badge trạng thái */
    .status-badge {
        font-size: 0.7rem;
        padding: 3px 8px;
        border-radius: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    /* Dùng rgba để badge xuyên thấu nhẹ, đẹp trên cả nền tối */
    .badge-free { background-color: rgba(40, 167, 69, 0.15); color: #28a745; }
    .badge-soon { background-color: rgba(255, 193, 7, 0.15); color: #d39e00; }
    .badge-busy { background-color: rgba(220, 53, 69, 0.15); color: #dc3545; }

    /* Thông tin chính */
    .info-primary {
        font-size: 1rem;
        margin-bottom: 4px;
        font-weight: 600;
        color: var(--text-color);
        opacity: 0.95;
    }
    .info-secondary {
        font-size: 0.85rem;
        color: var(--text-color);
        opacity: 0.7; /* Làm mờ text phụ */
    }

    /* 4. NÚT BẤM (CLEAN / GHOST STYLE) */
    div.stButton > button {
        width: 100%;
        border: none !important; /* BỎ VIỀN HOÀN TOÀN */
        background-color: transparent !important; /* NỀN TRONG SUỐT */
        color: #0d6efd !important; /* Chữ màu xanh */
        font-size: 0.9rem;
        font-weight: 600;
        padding: 10px 0;
        margin: 0 !important;
        border-top: 1px solid rgba(128, 128, 128, 0.1) !important; /* Gạch ngang mờ ngăn cách */
        border-radius: 0 !important;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: rgba(13, 110, 253, 0.05) !important; /* Hover lên màu xanh rất nhạt */
        color: #0a58ca !important;
        letter-spacing: 0.5px; /* Hiệu ứng giãn chữ nhẹ khi hover */
    }
    
    /* 5. CÁC THÀNH PHẦN KHÁC */
    div[data-testid="column"] { padding: 0 8px; }
    
    .header-info {
        background-color: var(--secondary-background-color);
        padding: 15px; border-radius: 12px;
        margin-bottom: 25px; 
        border: 1px solid rgba(128, 128, 128, 0.1);
        text-align: center;
    }
    
    .schedule-item {
        background-color: var(--secondary-background-color);
        border-left: 4px solid #0d6efd;
        padding: 12px; margin-bottom: 10px; border-radius: 6px;
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
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
                if sf.lower() == f.lower(): f = sf; break
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

# DEFAULT D3
if 'selected_building_state' not in st.session_state:
    st.session_state.selected_building_state = "D3"

st.title("🏫 Tra Cứu Phòng Trống BK")

try: df = load_and_process()
except Exception as e:
    st.error(f"Lỗi data: {e}")
    st.stop()

if df.empty:
    st.warning("Chưa tải được dữ liệu.")
    st.stop()

now = st.session_state.current_time
now_naive = now.replace(tzinfo=None)
delta = now_naive - START_DATE_K70
curr_week = (delta.days // 7) + 1 if delta.days >= 0 else 0
py_to_bk = {0: '2', 1: '3', 2: '4', 3: '5', 4: '6', 5: '7', 6: '8'}
curr_wd = py_to_bk.get(now.weekday(), '2')

# --- MÀN HÌNH DANH SÁCH ---
if st.session_state.view_mode == 'list':
    st.sidebar.header("🔍 Bộ Lọc")
    num_cols = st.sidebar.slider("Số cột hiển thị", 1, 4, 3, key="num_cols_slider")
    
    with st.sidebar.expander("🛠️ Chỉnh giờ"):
        if st.checkbox("Chỉnh tay", key="chk_manual"):
            d_v = st.date_input("Ngày", st.session_state.current_time, key="date_in")
            t_v = st.time_input("Giờ", st.session_state.current_time.time(), key="time_in")
            st.session_state.current_time = TZ_VN.localize(datetime.combine(d_v, t_v))
        else:
            if st.button("Cập nhật giờ", key="btn_upd"):
                st.session_state.current_time = datetime.now(TZ_VN)
                st.rerun()

    # BUILDING SELECT
    buildings = sorted([b for b in df['Building'].unique() if b != 'Khác'])
    try: def_idx = buildings.index(st.session_state.selected_building_state)
    except: def_idx = 0
    sel_b = st.sidebar.selectbox("📍 Chọn Tòa Nhà", buildings, index=def_idx, key="sel_b")
    st.session_state.selected_building_state = sel_b

    st.markdown(f"""
    <div class="header-info">
        <h3 style="margin:0; color:var(--text-color)">{now.strftime('%H:%M')} | Thứ {curr_wd} | {now.strftime('%d/%m/%Y')}</h3>
        <p style="margin:0; font-size:1.1rem; opacity:0.8; color:var(--text-color)">Tuần học: <b>{curr_week}</b></p>
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
                return "BUSY", f"Đang học: {x['name']}", f"Đến {x['end_str']} (Còn {l//60}h{l%60}p)", x['code']
        for x in slots:
            if x['start_val'] > c_hm:
                diff = x['start_val'] - c_hm
                t_str = f"{diff//60}h{diff%60}p" if diff//60 > 0 else f"{diff%60}p"
                if diff >= 45: return "FREE", f"Trống trong {t_str}", f"Sau: {x['name']} ({x['start_str']})", x['code']
                else: return "SOON", f"Sắp học trong {t_str}", f"Sau: {x['name']} ({x['start_str']})", x['code']
        
        return "FREE", "Trống đến hết ngày", "Thoải mái tự học", "NULL"

    rooms = sorted(df_b['MY_ROOM'].unique())
    results = []
    for r in rooms:
        r_sch = df_active[df_active['MY_ROOM'] == r]
        stt, msg1, msg2, code = get_room_status(r_sch, now)
        results.append({"r": r, "m1": msg1, "m2": msg2, "st": stt, "prio": {"FREE": 1, "SOON": 2, "BUSY": 3}[stt], "code": code})
    
    results.sort(key=lambda x: (x['prio'], x['r']))

    if not results:
        st.info(f"Không tìm thấy dữ liệu cho tòa {sel_b}.")
    else:
        chunk_size = num_cols
        for i in range(0, len(results), chunk_size):
            cols = st.columns(chunk_size)
            row_items = results[i:i+chunk_size]
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    if item['st'] == 'FREE': 
                        css_cls, badge_cls, badge_txt = "status-strip-free", "badge-free", "TRỐNG"
                    elif item['st'] == 'SOON': 
                        css_cls, badge_cls, badge_txt = "status-strip-soon", "badge-soon", "SẮP HỌC"
                    else: 
                        css_cls, badge_cls, badge_txt = "status-strip-busy", "badge-busy", "ĐANG HỌC"
                    
                    code_info = f"Mã: {item['code']}" if item['code'] and str(item['code']) != "NULL" else ""

                    st.markdown(f"""
                    <div class="room-card-box {css_cls}">
                        <div class="card-body">
                            <div class="card-header">
                                <span class="room-name">{item['r']}</span>
                                <span class="status-badge {badge_cls}">{badge_txt}</span>
                            </div>
                            <div class="info-primary">{item['m1']}</div>
                            <div class="info-secondary">{item['m2']}</div>
                            <div class="info-secondary" style="font-size:0.8rem; margin-top:4px">{code_info}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Nút bấm Clean (Không viền, text xanh)
                    if st.button("Xem chi tiết ➜", key=f"btn_{item['r']}_{idx}"):
                        st.session_state.selected_room_data = item['r']
                        st.session_state.view_mode = 'detail'
                        st.rerun()

# --- MÀN HÌNH CHI TIẾT ---
elif st.session_state.view_mode == 'detail':
    r_name = st.session_state.selected_room_data
    c1, c2 = st.columns([1, 6])
    with c1:
        st.write("")
        if st.button("⬅️ Quay lại", key="btn_back"):
            st.session_state.view_mode = 'list'
            st.rerun()
    with c2:
        st.markdown(f"## 📅 Lịch học: {r_name} (Tuần {curr_week})")
        
    df_week = df[
        (df['MY_ROOM'] == r_name) & 
        (df['Parsed_Weeks'].apply(lambda x: check_week(x, curr_week)))
    ].copy()
    
    st.divider()
    
    if df_week.empty:
        st.success("🎉 Tuần này phòng trống hoàn toàn!")
    else:
        df_week['Day_Sort'] = df_week['MY_DAY'].apply(lambda x: int(float(x)) if x else 0)
        df_week = df_week.sort_values(by=['Day_Sort', 'Start'])
        for _, row in df_week.iterrows():
            d = str(int(float(row['MY_DAY'])))
            st.markdown(f"""
            <div class="schedule-item">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:700; font-size:1.1rem; opacity:0.9">Thứ {d}</div>
                        <div style="opacity:0.7; font-size:0.9rem">{row['Start'][:2]}:{row['Start'][2:]} - {row['End'][:2]}:{row['End'][2:]}</div>
                    </div>
                    <div style="text-align:right">
                        <div style="color:#0d6efd; font-weight:600">{row['MY_NAME']}</div>
                        <div style="font-size:0.8rem; opacity:0.8;">Mã lớp: <b>{row['MY_CODE']}</b></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
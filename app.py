import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="BK Room Finder", page_icon="🏫", layout="wide")

# --- 2. CSS (GIAO DIỆN DASHBOARD CHUYÊN NGHIỆP) ---
st.markdown("""
<style>
    /* Tổng thể Card */
    .room-card-box {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e5e7eb;
        margin-bottom: 10px;
        overflow: hidden;
        transition: transform 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .room-card-box:hover {
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transform: translateY(-2px);
        border-color: #d1d5db;
    }

    /* Dải màu trạng thái bên trái */
    .status-strip-free { border-left: 5px solid #10b981; } /* Xanh ngọc */
    .status-strip-soon { border-left: 5px solid #f59e0b; } /* Cam vàng */
    .status-strip-busy { border-left: 5px solid #ef4444; } /* Đỏ */

    /* Nội dung bên trong */
    .card-body {
        padding: 12px 15px;
        flex-grow: 1;
    }

    /* Header: Tên phòng + Icon */
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 8px;
    }
    .room-name {
        font-size: 1.2rem;
        font-weight: 700;
        color: #111827;
        margin: 0;
    }
    
    /* Badge trạng thái nhỏ góc phải */
    .status-badge {
        font-size: 0.7rem;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-free { background-color: #d1fae5; color: #065f46; }
    .badge-soon { background-color: #fef3c7; color: #92400e; }
    .badge-busy { background-color: #fee2e2; color: #991b1b; }

    /* Thông tin chính */
    .info-text {
        font-size: 0.9rem;
        color: #4b5563;
        line-height: 1.4;
        margin-bottom: 4px;
    }
    .highlight-time { font-weight: 600; color: #111827; }
    
    /* Thông tin phụ (Mã lớp, Tiết sau) */
    .sub-text {
        font-size: 0.8rem;
        color: #6b7280;
        margin-top: 6px;
        display: flex;
        align-items: center;
        gap: 5px;
    }

    /* Custom Button của Streamlit: Biến thành thanh footer */
    div.stButton > button {
        width: 100%;
        border-radius: 0;
        border: none;
        border-top: 1px solid #f3f4f6;
        background-color: #f9fafb;
        color: #2563eb; /* Màu xanh link */
        font-size: 0.85rem;
        font-weight: 500;
        padding: 8px 0;
        margin: 0 !important;
        transition: background 0.2s;
    }
    div.stButton > button:hover {
        background-color: #eff6ff;
        color: #1d4ed8;
    }

    /* Layout Header trang web */
    .page-header {
        background: white; padding: 15px 20px; 
        border-radius: 10px; border: 1px solid #e5e7eb;
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 20px;
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

# --- 4. LOAD DATA (CACHE_DATA) ---
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
    # Thanh Header thông tin
    st.markdown(f"""
    <div class="page-header">
        <div>
            <div style="font-size:1.5rem; font-weight:800; color:#111827">{now.strftime('%H:%M')}</div>
            <div style="color:#6b7280; font-weight:500">Thứ {curr_wd}, {now.strftime('%d/%m/%Y')}</div>
        </div>
        <div style="text-align:right">
            <div style="font-size:0.9rem; color:#6b7280">Tuần học</div>
            <div style="font-size:1.5rem; font-weight:800; color:#2563eb">{curr_week}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    st.sidebar.header("🔍 Bộ Lọc")
    num_cols = st.sidebar.slider("Số cột", 1, 4, 3, key="num_cols_slider")
    
    with st.sidebar.expander("🛠️ Chỉnh giờ"):
        if st.checkbox("Chỉnh tay", key="chk_manual"):
            d_v = st.date_input("Ngày", st.session_state.current_time, key="date_in")
            t_v = st.time_input("Giờ", st.session_state.current_time.time(), key="time_in")
            st.session_state.current_time = TZ_VN.localize(datetime.combine(d_v, t_v))
        else:
            if st.button("Cập nhật giờ", key="btn_upd"):
                st.session_state.current_time = datetime.now(TZ_VN)
                st.rerun()

    buildings = sorted([b for b in df['Building'].unique() if b != 'Khác'])
    sel_b = st.sidebar.selectbox("📍 Chọn Tòa Nhà", buildings, key="sel_b")

    df_b = df[df['Building'] == sel_b]
    df_today = df_b[df_b['MY_DAY'].apply(clean_day) == curr_wd]
    df_active = df_today[df_today['Parsed_Weeks'].apply(lambda x: check_week(x, curr_week))]

    # Logic Status
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
        
        # 1. Busy
        for x in slots:
            if x['start_val'] <= c_hm <= x['end_val']:
                l = x['end_val'] - c_hm
                return "BUSY", f"Đang học: {x['name']}", f"Đến {x['end_str']} ({l//60}h{l%60}p)", x['code']
        # 2. Soon
        for x in slots:
            if x['start_val'] > c_hm:
                diff = x['start_val'] - c_hm
                t_str = f"{diff//60}h{diff%60}p" if diff//60 > 0 else f"{diff%60}p"
                
                if diff >= 45: 
                    return "FREE", f"Trống trong {t_str}", f"Sau: {x['name']} ({x['start_str']})", x['code']
                else: 
                    return "SOON", f"Sắp học trong {t_str}", f"Sau: {x['name']} ({x['start_str']})", x['code']
        
        return "FREE", "Trống đến hết ngày", "Thoải mái tự học", "NULL"

    rooms = sorted(df_b['MY_ROOM'].unique())
    results = []
    for r in rooms:
        r_sch = df_active[df_active['MY_ROOM'] == r]
        # Hàm trả về 4 biến: Status, Main Msg, Sub Msg, Code
        stt, msg1, msg2, code = get_room_status(r_sch, now)
        results.append({"r": r, "m1": msg1, "m2": msg2, "st": stt, "prio": {"FREE": 1, "SOON": 2, "BUSY": 3}[stt], "code": code})
    
    results.sort(key=lambda x: (x['prio'], x['r']))

    # RENDER GRID
    if not results:
        st.info("Không có dữ liệu.")
    else:
        chunk_size = num_cols
        for i in range(0, len(results), chunk_size):
            cols = st.columns(chunk_size)
            row_items = results[i:i+chunk_size]
            
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    # Config Style
                    if item['st'] == 'FREE': 
                        css_class, badge_cls, badge_txt = "status-strip-free", "badge-free", "TRỐNG"
                    elif item['st'] == 'SOON': 
                        css_class, badge_cls, badge_txt = "status-strip-soon", "badge-soon", "SẮP HỌC"
                    else: 
                        css_class, badge_cls, badge_txt = "status-strip-busy", "badge-busy", "ĐANG HỌC"
                    
                    code_info = f"Mã: {item['code']}" if item['code'] and item['code'] != "NULL" else ""

                    # Render HTML Card
                    st.markdown(f"""
                    <div class="room-card-box {css_class}">
                        <div class="card-body">
                            <div class="card-header">
                                <h3 class="room-name">{item['r']}</h3>
                                <span class="status-badge {badge_cls}">{badge_txt}</span>
                            </div>
                            <div class="info-text highlight-time">{item['m1']}</div>
                            <div class="info-text">{item['m2']}</div>
                            <div class="sub-text">
                                <span>📌 {code_info}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Nút bấm tàng hình (Footer)
                    if st.button("Xem lịch chi tiết ➜", key=f"btn_{item['r']}_{idx}"):
                        st.session_state.selected_room_data = item['r']
                        st.session_state.view_mode = 'detail'
                        st.rerun()

# --- MÀN HÌNH CHI TIẾT ---
elif st.session_state.view_mode == 'detail':
    r_name = st.session_state.selected_room_data
    c1, c2 = st.columns([1, 6])
    with c1:
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
            <div style="background:white; border-left:4px solid #2563eb; padding:15px; margin-bottom:10px; border-radius:8px; box-shadow:0 1px 2px rgba(0,0,0,0.05); display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-weight:700; font-size:1.1rem; color:#1f2937">Thứ {d}</div>
                    <div style="color:#4b5563; font-size:0.9rem">{row['Start'][:2]}:{row['Start'][2:]} - {row['End'][:2]}:{row['End'][2:]}</div>
                </div>
                <div style="text-align:right">
                    <div style="color:#d97706; font-weight:600">{row['MY_NAME']}</div>
                    <div style="font-size:0.8rem; color:#9ca3af; background:#f3f4f6; padding:2px 6px; border-radius:4px; display:inline-block; margin-top:4px">{row['MY_CODE']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
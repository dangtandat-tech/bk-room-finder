import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="BK Room Finder", page_icon="🏫", layout="wide")

# --- 2. CSS (RESET VỀ GIAO DIỆN CHUẨN ĐẸP) ---
st.markdown("""
<style>
    /* Card Container */
    .room-card-wrapper {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        background: white;
        border: 1px solid #e0e0e0;
    }

    /* Phần trên: Thông tin chính (Màu sắc) */
    .card-header {
        padding: 12px 15px;
        color: white;
    }
    .bg-free { background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%); }
    .bg-soon { background: linear-gradient(135deg, #ffc107 0%, #d39e00 100%); color: #212529 !important; }
    .bg-busy { background: linear-gradient(135deg, #dc3545 0%, #bd2130 100%); }

    .room-title {
        font-size: 1.25rem; font-weight: 800;
        display: flex; justify-content: space-between; align-items: center;
    }
    .room-sub { font-size: 0.9rem; margin-top: 5px; opacity: 0.95; line-height: 1.4; font-weight: 500; }
    
    /* Badge Mã Lớp */
    .code-badge {
        font-size: 0.75rem; background: rgba(255,255,255,0.3);
        padding: 3px 8px; border-radius: 4px; font-weight: bold;
    }

    /* Phần dưới: Nút bấm (Tách riêng để không lỗi layout) */
    .card-footer {
        padding: 0; /* Để nút bấm tràn viền */
        background: #f8f9fa;
    }
    
    /* Chỉnh nút bấm Streamlit cho khớp vào Footer */
    div.stButton > button {
        width: 100%;
        border-radius: 0 0 10px 10px; /* Bo góc dưới */
        border: none;
        border-top: 1px solid #eee;
        background-color: transparent;
        color: #0d6efd;
        font-weight: 600;
        padding: 8px 0;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #e9ecef;
        color: #0056b3;
    }

    /* Layout */
    .header-info {
        background-color: #f8f9fa; padding: 15px; border-radius: 10px;
        margin-bottom: 20px; border: 1px solid #dee2e6; text-align: center; color: #333;
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
            else: res.append(int(p))
    except: pass
    return res

def parse_time(t_str):
    if pd.isna(t_str) or '-' not in str(t_str): return None, None
    try:
        s, e = str(t_str).split('-')
        return s.strip().zfill(4), e.strip().zfill(4)
    except: return None, None

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

st.title("🏫 Tra Cứu Phòng Trống BK")

try: df = load_and_process()
except: st.stop()

if df.empty: st.stop()

now = st.session_state.current_time
now_naive = now.replace(tzinfo=None)
delta = now_naive - START_DATE_K70
curr_week = (delta.days // 7) + 1 if delta.days >= 0 else 0
py_to_bk = {0: '2', 1: '3', 2: '4', 3: '5', 4: '6', 5: '7', 6: '8'}
curr_wd = py_to_bk.get(now.weekday(), '2')

# --- VIEW: LIST ---
if st.session_state.view_mode == 'list':
    st.sidebar.header("🔍 Bộ Lọc")
    # Thanh trượt số cột (Quan trọng để fix lỗi hiển thị)
    num_cols = st.sidebar.slider("Số cột hiển thị", 1, 4, 3) 
    
    with st.sidebar.expander("🛠️ Chỉnh giờ"):
        if st.checkbox("Chỉnh tay"):
            d_v = st.date_input("Ngày", st.session_state.current_time)
            t_v = st.time_input("Giờ", st.session_state.current_time.time())
            st.session_state.current_time = TZ_VN.localize(datetime.combine(d_v, t_v))
        else:
            if st.button("Cập nhật giờ"):
                st.session_state.current_time = datetime.now(TZ_VN)
                st.rerun()

    buildings = sorted([b for b in df['Building'].unique() if b != 'Khác'])
    sel_b = st.sidebar.selectbox("📍 Chọn Tòa Nhà", buildings)

    st.markdown(f"""
    <div class="header-info">
        <h3 style="margin:0; color:#d63384">{now.strftime('%H:%M')} | Thứ {curr_wd} | {now.strftime('%d/%m/%Y')}</h3>
        <p style="margin:0">Tuần học: <b>{curr_week}</b></p>
    </div>
    """, unsafe_allow_html=True)

    df_b = df[df['Building'] == sel_b]
    df_today = df_b[df_b['MY_DAY'].apply(clean_day) == curr_wd]
    df_active = df_today[df_today['Parsed_Weeks'].apply(lambda x: check_week(x, curr_week))]

    def get_status(schedule, c_time_full):
        c_hm = c_time_full.hour * 60 + c_time_full.minute
        slots = []
        for _, row in schedule.iterrows():
            try:
                sh, sm = int(row['Start'][:2]), int(row['Start'][2:])
                eh, em = int(row['End'][:2]), int(row['End'][2:])
                slots.append({'s': sh*60+sm, 'e': eh*60+em, 'n': row['MY_NAME'], 'c': row['MY_CODE'], 'es': f"{eh:02d}:{em:02d}", 'ss': f"{sh:02d}:{sm:02d}"})
            except: continue
        slots.sort(key=lambda x: x['s'])
        
        for x in slots:
            if x['s'] <= c_hm <= x['e']:
                l = x['e'] - c_hm
                return "BUSY", f"ĐANG HỌC: {x['n']}<br>Đến: {x['es']} (Còn {l//60}h{l%60}p)", 3, x['c']
        for x in slots:
            if x['s'] > c_hm:
                diff = x['s'] - c_hm
                t_str = f"{diff//60}h{diff%60}p" if diff//60 > 0 else f"{diff%60}p"
                next_txt = f"Sau: {x['n']} ({x['ss']})"
                if diff >= 45: return "FREE", f"TRỐNG: {t_str}<br>{next_txt}", 1, x['c']
                else: return "SOON", f"Sắp học trong {t_str}<br>{next_txt}", 2, x['c']
        return "FREE", "TRỐNG đến hết ngày hôm nay", 0, "NULL"

    rooms = sorted(df_b['MY_ROOM'].unique())
    results = []
    for r in rooms:
        r_sch = df_active[df_active['MY_ROOM'] == r]
        stt, msg, prio, code = get_status(r_sch, now)
        results.append({"r": r, "msg": msg, "st": stt, "prio": prio, "code": code})
    
    results.sort(key=lambda x: (x['prio'], x['r']))

    if not results:
        st.info("Không có dữ liệu.")
    else:
        # GRID RENDER
        chunk_size = num_cols
        for i in range(0, len(results), chunk_size):
            cols = st.columns(chunk_size)
            for idx, item in enumerate(results[i:i+chunk_size]):
                with cols[idx]:
                    if item['st'] == 'FREE': bg_cls, icon = "bg-free", "✅"
                    elif item['st'] == 'SOON': bg_cls, icon = "bg-soon", "⚠️"
                    else: bg_cls, icon = "bg-busy", "⛔"
                    
                    code_html = f'<span class="code-badge">{item["code"]}</span>' if item['code'] and item['code'] != "NULL" else ""

                    # Wrapper
                    st.markdown(f"""
                    <div class="room-card-wrapper">
                        <div class="card-header {bg_cls}">
                            <div class="room-title">
                                <span>{icon} {item['r']}</span>
                                {code_html}
                            </div>
                            <div class="room-sub">{item['msg']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Nút bấm riêng biệt (Không bị lỗi CSS)
                    if st.button("📅 Xem chi tiết", key=f"btn_{item['r']}"):
                        st.session_state.selected_room_data = item['r']
                        st.session_state.view_mode = 'detail'
                        st.rerun()

# --- VIEW: DETAIL ---
elif st.session_state.view_mode == 'detail':
    r_name = st.session_state.selected_room_data
    c1, c2 = st.columns([1, 6])
    with c1:
        if st.button("⬅️ Quay lại"):
            st.session_state.view_mode = 'list'
            st.rerun()
    with c2:
        st.markdown(f"## 📅 Lịch học: **{r_name}** (Tuần {curr_week})")
        
    df_week = df[
        (df['MY_ROOM'] == r_name) & 
        (df['Parsed_Weeks'].apply(lambda x: check_week(x, curr_week)))
    ].copy()
    
    if df_week.empty:
        st.info("Tuần này phòng trống hoàn toàn.")
    else:
        df_week['Day_Sort'] = df_week['MY_DAY'].apply(lambda x: int(float(x)) if x else 0)
        df_week = df_week.sort_values(by=['Day_Sort', 'Start'])
        for _, row in df_week.iterrows():
            d = str(int(float(row['MY_DAY'])))
            st.markdown(f"""
            <div style="background:white; border-left:5px solid #0d6efd; padding:15px; margin-bottom:10px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1); color:#333;">
                <div style="font-weight:bold; font-size:1.1rem">Thứ {d} | {row['Start'][:2]}:{row['Start'][2:]} - {row['End'][:2]}:{row['End'][2:]}</div>
                <div style="color:#d63384; font-weight:600">{row['MY_NAME']}</div>
                <div style="font-size:0.9rem; color:#666">Mã lớp: {row['MY_CODE']}</div>
            </div>
            """, unsafe_allow_html=True)
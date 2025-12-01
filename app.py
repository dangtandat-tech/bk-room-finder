import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="BK Room Finder",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TÙY CHỈNH (COMPACT STYLE) ---
st.markdown("""
<style>
    .room-card {
        padding: 8px 12px;
        border-radius: 6px;
        margin-bottom: 8px;
        color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: transform 0.1s;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .room-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    
    .status-free { background-color: #28a745; border-left: 4px solid #145523; } /* Xanh */
    .status-soon { background-color: #ffc107; color: #212529 !important; border-left: 4px solid #9c7500; } /* Vàng */
    .status-busy { background-color: #dc3545; border-left: 4px solid #881622; } /* Đỏ */

    .room-name {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 2px;
        display: flex; align-items: center; gap: 8px;
    }
    .room-status {
        font-size: 0.85rem;
        line-height: 1.3;
        opacity: 0.95;
    }
    
    .header-info {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 15px;
        border: 1px solid #dee2e6;
        text-align: center;
        color: #333;
    }
    div[data-testid="column"] { padding: 0 4px; }
</style>
""", unsafe_allow_html=True)

START_DATE_K70 = datetime(2025, 9, 8)

# --- 3. XỬ LÝ DỮ LIỆU ---
@st.cache(allow_output_mutation=True)
def load_and_process_data():
    files = ['data1.csv', 'data2.csv', 'TKB20251-K70.xlsx - Sheet1.csv', 'TKB20251-Full1.xlsx - Sheet1.csv']
    dfs = []
    encodings = ['utf-8-sig', 'utf-16', 'utf-8', 'cp1258', 'latin1']
    
    for f in files:
        if not os.path.exists(f): continue
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
    def find_col(kws):
        for c in cols:
            for kw in kws:
                if kw.lower() in c.lower(): return c
        return None

    c_room = find_col(['phòng', 'phong'])
    c_week = find_col(['tuần', 'tuan'])
    c_time = find_col(['thời_gian', 'thoi_gian', 'time'])
    c_day  = find_col(['thứ', 'thu', 'day'])
    c_name = find_col(['tên_hp', 'ten_hp', 'name'])
    
    if not c_room or not c_time:
        st.error("⚠️ Thiếu cột Phòng/Thời gian trong file CSV.")
        return pd.DataFrame()

    df = pd.DataFrame()
    df['MY_ROOM'] = df_raw[c_room]
    df['MY_WEEK'] = df_raw[c_week] if c_week else ""
    df['MY_TIME'] = df_raw[c_time]
    df['MY_DAY']  = df_raw[c_day] if c_day else "2"
    df['MY_NAME'] = df_raw[c_name] if c_name else "Lớp học"
    
    df = df.dropna(subset=['MY_ROOM', 'MY_TIME'])
    df = df[df['MY_ROOM'] != 'NULL']

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
    df['Parsed_Weeks'] = df['MY_WEEK'].apply(lambda x: ",".join(map(str, parse_weeks(x))))

    def parse_t(t_str):
        if pd.isna(t_str) or '-' not in str(t_str): return None, None
        try:
            s, e = str(t_str).split('-')
            return s.strip().zfill(4), e.strip().zfill(4)
        except: return None, None
    t_parsed = df['MY_TIME'].apply(parse_t)
    df['Start'] = t_parsed.apply(lambda x: x[0])
    df['End'] = t_parsed.apply(lambda x: x[1])
    df = df.dropna(subset=['Start', 'End'])

    def extract_building(room_name):
        s = str(room_name).strip()
        if '-' in s: return s.split('-')[0]
        return "Khác"
        
    df['Building'] = df['MY_ROOM'].apply(extract_building)
    return df

# --- 4. LOGIC CHÍNH ---
st.title("🏫 Tra Cứu Phòng Trống BK")

df = load_and_process_data()
if df.empty: st.stop()

# Sidebar
st.sidebar.header("🔍 Bộ Lọc")
with st.sidebar.expander("🛠️ Chỉnh giờ (Test)"):
    if st.checkbox("Bật chỉnh tay"):
        d_input = st.date_input("Ngày", datetime.now())
        t_input = st.time_input("Giờ", datetime.now().time())
        now = datetime.combine(d_input, t_input)
    else:
        now = datetime.now()
        if st.button("Cập nhật giờ"): st.experimental_rerun()

delta = now - START_DATE_K70
curr_week = (delta.days // 7) + 1 if delta.days >= 0 else 0
py_to_bk = {0: '2', 1: '3', 2: '4', 3: '5', 4: '6', 5: '7', 6: '8'}
curr_wd = py_to_bk.get(now.weekday(), '2')

st.markdown(f"""
<div class="header-info">
    <div style="font-size: 1.1rem; font-weight: bold; color: #d63384;">
        {now.strftime('%H:%M')} | Thứ {curr_wd} | Ngày {now.strftime('%d/%m/%Y')}
    </div>
    <div style="font-size: 0.9rem; color: #666;">Tuần học: <b>{curr_week}</b></div>
</div>
""", unsafe_allow_html=True)

buildings = sorted([b for b in df['Building'].unique() if b != 'Khác'])
selected_b = st.sidebar.selectbox("📍 Chọn Tòa Nhà", buildings)

df_b = df[df['Building'] == selected_b]
def clean_day(v):
    try: return str(int(float(v)))
    except: return str(v)
df_today = df_b[df_b['MY_DAY'].apply(clean_day) == curr_wd]
def check_week(w, cw): return str(cw) in str(w).split(',')
df_active = df_today[df_today['Parsed_Weeks'].apply(lambda x: check_week(x, curr_week))]

# --- HÀM CHECK STATUS ---
def get_status(schedule, c_time):
    slots = []
    for _, row in schedule.iterrows():
        try:
            sh, sm = int(row['Start'][:2]), int(row['Start'][2:])
            eh, em = int(row['End'][:2]), int(row['End'][2:])
            s_dt = c_time.replace(hour=sh, minute=sm, second=0)
            e_dt = c_time.replace(hour=eh, minute=em, second=0)
            slots.append((s_dt, e_dt, row['MY_NAME']))
        except: continue
    
    slots.sort(key=lambda x: x[0])
    
    # 1. Đang học (ĐỎ)
    for s, e, n in slots:
        if s <= c_time <= e:
            l = e - c_time
            h, m = l.seconds//3600, (l.seconds//60)%60
            return "BUSY", f"Đang học: {n}<br>Đến: {e.strftime('%H:%M')} (Còn {h}h {m}p)", 3
            
    # 2. Sắp học (VÀNG/XANH)
    for s, e, n in slots:
        if s > c_time:
            diff = (s - c_time).total_seconds()/60
            h, m = int(diff//60), int(diff%60)
            t_str = f"{h}h {m}p" if h>0 else f"{m}p"
            
            # Thông báo tiết sau
            next_info = f"Tiết sau: {n}<br>Bắt đầu: <b>{s.strftime('%H:%M')}</b>"
            
            if diff >= 45: # Trống >= 45p -> Xanh
                return "FREE", f"TRỐNG: {t_str}<br>{next_info}", 1
            else: # Trống < 45p -> Vàng
                return "SOON", f"Sắp học trong {t_str}<br>{next_info}", 2
                
    # 3. Hết lịch -> XANH
    return "FREE", "TRỐNG đến hết ngày hôm nay", 0

# --- HIỂN THỊ ---
rooms = sorted(df_b['MY_ROOM'].unique())
results = []

for r in rooms:
    r_sch = df_active[df_active['MY_ROOM'] == r]
    stt, msg, prio = get_status(r_sch, now)
    results.append({"r": r, "msg": msg, "st": stt, "prio": prio})

results.sort(key=lambda x: (x['prio'], x['r']))

cols = st.columns(4) # Grid 4 cột
if not results:
    st.info(f"Không có dữ liệu cho tòa {selected_b}.")
else:
    for i, item in enumerate(results):
        if item['st'] == 'FREE': cls, icon = "status-free", "✅"
        elif item['st'] == 'SOON': cls, icon = "status-soon", "⚠️"
        else: cls, icon = "status-busy", "⛔"
        
        html = f"""
        <div class="room-card {cls}">
            <div class="room-name">{icon} {item['r']}</div>
            <div class="room-status">{item['msg']}</div>
        </div>
        """
        with cols[i % 4]:
            st.markdown(html, unsafe_allow_html=True)
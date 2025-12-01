import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="BK Room Finder", page_icon="🏫", layout="wide")

# --- 2. CSS ---
st.markdown("""
<style>
    /* Card */
    .room-card {
        padding: 10px; border-radius: 8px; margin-bottom: 10px;
        color: white; border: 1px solid rgba(255,255,255,0.1);
        cursor: pointer; position: relative;
    }
    .status-free { background-color: #28a745; border-left: 4px solid #145523; }
    .status-soon { background-color: #ffc107; color: #212529 !important; border-left: 4px solid #9c7500; }
    .status-busy { background-color: #dc3545; border-left: 4px solid #881622; }
    
    .room-name { font-size: 1.2rem; font-weight: 700; display: flex; align-items: center; gap: 8px; }
    .room-status { font-size: 0.85rem; line-height: 1.3; margin-top: 4px;}
    .class-code { 
        font-size: 0.75rem; background: rgba(0,0,0,0.2); 
        padding: 2px 6px; border-radius: 4px; margin-left: auto;
    }
    
    /* Header */
    .header-info {
        background-color: #f8f9fa; padding: 10px; border-radius: 8px;
        margin-bottom: 15px; border: 1px solid #dee2e6; text-align: center; color: #333;
    }
    
    /* Expander lịch tuần */
    .streamlit-expanderHeader { font-weight: bold; color: #0d6efd; }
    .schedule-table { font-size: 0.85rem; width: 100%; border-collapse: collapse; }
    .schedule-table th, .schedule-table td { border: 1px solid #ddd; padding: 4px; text-align: left; }
    .schedule-table th { background-color: #f2f2f2; }
</style>
""", unsafe_allow_html=True)

START_DATE_K70 = datetime(2025, 9, 8)
TZ_VN = pytz.timezone('Asia/Ho_Chi_Minh')

# --- 3. DATA PROCESSING ---
@st.cache(allow_output_mutation=True)
def load_data():
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

    # Auto-detect cols
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
    c_code = fc(['mã_lớp', 'ma_lop', 'class_id']) # Thêm cột Mã lớp

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

    # Parse Time
    def parse_t(t):
        if pd.isna(t) or '-' not in str(t): return None, None
        try: s, e = str(t).split('-'); return s.strip().zfill(4), e.strip().zfill(4)
        except: return None, None
    
    tp = df['MY_TIME'].apply(parse_t)
    df['Start'] = tp.apply(lambda x: x[0])
    df['End'] = tp.apply(lambda x: x[1])
    df = df.dropna(subset=['Start', 'End'])

    # Parse Weeks
    def parse_w(w):
        if pd.isna(w): return []
        res = []
        try:
            parts = str(w).replace('"', '').split(',')
            for p in parts:
                if '-' in p: s, e = map(int, p.split('-')); res.extend(range(s, e+1))
                else: res.append(int(p))
        except: pass
        return res
    df['Parsed_Weeks'] = df['MY_WEEK'].apply(lambda x: ",".join(map(str, parse_weeks(x))))

    # Building
    df['Building'] = df['MY_ROOM'].apply(lambda x: str(x).split('-')[0] if '-' in str(x) else "Khác")
    return df

# --- 4. APP LOGIC ---
st.title("🏫 Tra Cứu Phòng Trống BK")

df = load_data()
if df.empty:
    st.error("Không có dữ liệu.")
    st.stop()

# --- SIDEBAR & TIME CONTROL (Đã Fix lỗi nhảy giờ) ---
# Logic: Chỉ update giờ khi bấm nút "Cập nhật" hoặc chưa có session_state
if 'current_time' not in st.session_state:
    st.session_state.current_time = datetime.now(TZ_VN)

with st.sidebar.expander("🛠️ Chỉnh giờ (Test)"):
    mode = st.radio("Chế độ:", ["Tự động (Realtime)", "Chỉnh tay"], index=0)
    
    if mode == "Chỉnh tay":
        # Lấy giá trị cũ trong session state để hiển thị
        d_val = st.date_input("Ngày", st.session_state.current_time)
        t_val = st.time_input("Giờ", st.session_state.current_time.time())
        # Cập nhật session state ngay khi user đổi input
        new_dt = datetime.combine(d_val, t_val)
        st.session_state.current_time = TZ_VN.localize(new_dt)
    else:
        # Chế độ tự động
        if st.button("🔄 Cập nhật giờ hiện tại"):
            st.session_state.current_time = datetime.now(TZ_VN)

now = st.session_state.current_time
now_naive = now.replace(tzinfo=None)
delta = now_naive - START_DATE_K70
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

# Filter
buildings = sorted([b for b in df['Building'].unique() if b != 'Khác'])
sel_b = st.sidebar.selectbox("📍 Chọn Tòa Nhà", buildings)

df_b = df[df['Building'] == sel_b]

# Helper functions
def clean_day(v):
    try: return str(int(float(v)))
    except: return str(v)

def check_week(w, cw): return str(cw) in str(w).split(',')

# Lọc data hôm nay
df_today = df_b[df_b['MY_DAY'].apply(clean_day) == curr_wd]
df_today_active = df_today[df_today['Parsed_Weeks'].apply(lambda x: check_week(x, curr_week))]

# --- CHECK STATUS (Logic hiển thị mã lớp) ---
def get_status(schedule, c_time_full):
    c_hm = c_time_full.hour * 60 + c_time_full.minute
    slots = []
    
    for _, row in schedule.iterrows():
        try:
            sh, sm = int(row['Start'][:2]), int(row['Start'][2:])
            eh, em = int(row['End'][:2]), int(row['End'][2:])
            s_val = sh * 60 + sm
            e_val = eh * 60 + em
            slots.append({
                's': s_val, 'e': e_val, 
                'name': row['MY_NAME'], 
                'code': row['MY_CODE'],
                's_str': f"{sh:02d}:{sm:02d}", 
                'e_str': f"{eh:02d}:{em:02d}"
            })
        except: continue
    
    slots.sort(key=lambda x: x['s'])
    
    # 1. Busy
    for x in slots:
        if x['s'] <= c_hm <= x['e']:
            l = x['e'] - c_hm
            h, m = l // 60, l % 60
            return "BUSY", f"Đang học: {x['name']}<br>Đến: {x['e_str']} (Còn {h}h {m}p)", 3, x['code']
            
    # 2. Soon
    for x in slots:
        if x['s'] > c_hm:
            diff = x['s'] - c_hm
            h, m = diff // 60, diff % 60
            t_str = f"{h}h {m}p" if h > 0 else f"{m}p"
            next_msg = f"Tiết sau: {x['name']}<br>Bắt đầu: <b>{x['s_str']}</b>"
            
            if diff >= 45: 
                return "FREE", f"TRỐNG: {t_str}<br>{next_msg}", 1, x['code']
            else: 
                return "SOON", f"Sắp học trong {t_str}<br>{next_msg}", 2, x['code']
                
    return "FREE", "TRỐNG đến hết ngày hôm nay", 0, ""

# --- HIỂN THỊ ---
rooms = sorted(df_b['MY_ROOM'].unique())
results = []

for r in rooms:
    r_sch = df_today_active[df_today_active['MY_ROOM'] == r]
    stt, msg, prio, code = get_status(r_sch, now)
    results.append({"r": r, "msg": msg, "st": stt, "prio": prio, "code": code})

results.sort(key=lambda x: (x['prio'], x['r']))

# --- GRID LAYOUT ---
if not results:
    st.info(f"Không có dữ liệu cho tòa {sel_b}.")
else:
    # Render từng row (4 cols)
    chunk_size = 4
    for i in range(0, len(results), chunk_size):
        row_items = results[i:i+chunk_size]
        cols = st.columns(chunk_size)
        
        for idx, item in enumerate(row_items):
            # CSS Class
            if item['st'] == 'FREE': cls, icon = "status-free", "✅"
            elif item['st'] == 'SOON': cls, icon = "status-soon", "⚠️"
            else: cls, icon = "status-busy", "⛔"
            
            # HTML Card
            # Nếu có mã lớp (code) thì hiện, không thì ẩn
            code_html = f'<span class="class-code">{item["code"]}</span>' if item["code"] and item["st"] != "FREE" else ""
            
            # Logic hiển thị mã lớp ở Card Xanh (Tiết tiếp theo)
            # Ở phần get_status đã trả về mã lớp của tiết tiếp theo rồi -> item['code'] có giá trị
            if item['st'] == 'FREE' and item['code']:
                code_html = f'<span class="class-code">Next: {item["code"]}</span>'

            card_html = f"""
            <div class="room-card {cls}">
                <div class="room-name">
                    <span>{icon} {item['r']}</span>
                    {code_html}
                </div>
                <div class="room-status">{item['msg']}</div>
            </div>
            """
            
            with cols[idx]:
                st.markdown(card_html, unsafe_allow_html=True)
                
                # --- TÍNH NĂNG XEM LỊCH TUẦN ---
                with st.expander("📅 Xem lịch tuần"):
                    # Lấy toàn bộ lịch của phòng này trong tuần hiện tại
                    # Lọc theo Tuần hiện tại + Phòng này (Không lọc Thứ)
                    df_week = df_b[
                        (df_b['MY_ROOM'] == item['r']) & 
                        (df_b['Parsed_Weeks'].apply(lambda x: check_week(x, curr_week)))
                    ].copy()
                    
                    if df_week.empty:
                        st.caption("Tuần này không có lịch học.")
                    else:
                        # Sắp xếp theo Thứ -> Giờ bắt đầu
                        df_week['Day_Int'] = df_week['MY_DAY'].apply(lambda x: int(float(x)) if x else 0)
                        df_week = df_week.sort_values(by=['Day_Int', 'Start'])
                        
                        # Hiển thị bảng mini
                        for _, row in df_week.iterrows():
                            d = str(int(float(row['MY_DAY'])))
                            st.markdown(f"""
                            <div style="font-size: 0.85rem; border-bottom:1px solid #eee; padding: 4px 0;">
                                <b>Thứ {d}</b> | {row['Start'][:2]}:{row['Start'][2:]}-{row['End'][:2]}:{row['End'][2:]}<br>
                                {row['MY_NAME']} <i style="color:#888">({row['MY_CODE']})</i>
                            </div>
                            """, unsafe_allow_html=True)
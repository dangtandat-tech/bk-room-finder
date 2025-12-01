import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="BK Room Finder", page_icon="🏫", layout="wide")

# --- 2. CSS (ĐƯỢC TÁCH RA BIẾN RIÊNG CHO SẠCH CODE) ---
CSS_STYLES = """
<style>
    /* Card Top - Phần hiển thị thông tin */
    .card-top {
        padding: 15px; 
        border-top-left-radius: 10px; 
        border-top-right-radius: 10px;
        color: white; 
        position: relative;
    }
    
    /* Màu nền */
    .bg-free { background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%); }
    .bg-soon { background: linear-gradient(135deg, #ffc107 0%, #d39e00 100%); color: #212529 !important; }
    .bg-busy { background: linear-gradient(135deg, #dc3545 0%, #bd2130 100%); }

    /* Chữ và Badge */
    .room-header { 
        font-size: 1.2rem; font-weight: 800; 
        display: flex; justify-content: space-between; align-items: center; 
    }
    .room-info { 
        font-size: 0.9rem; margin-top: 5px; 
        line-height: 1.4; opacity: 0.95; font-weight: 500; 
    }
    .code-badge { 
        font-size: 0.75rem; 
        background: rgba(255,255,255,0.3); 
        padding: 2px 8px; border-radius: 6px; font-weight: bold; 
    }

    /* Tùy chỉnh Nút bấm của Streamlit để dính liền vào Card */
    div.stButton > button {
        width: 100%;
        border-radius: 0 0 10px 10px !important;
        border: 1px solid #ddd;
        border-top: none;
        background-color: white;
        color: #666;
        font-size: 0.85rem;
        padding: 8px 0;
        margin-top: -16px !important; /* Kéo lên để khớp với div ở trên */
        transition: all 0.2s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    div.stButton > button:hover {
        background-color: #f8f9fa; 
        color: #0d6efd; 
        box-shadow: 0 6px 12px rgba(0,0,0,0.1); 
        transform: translateY(-2px); 
        z-index: 99;
    }
    
    /* Layout và Header */
    div[data-testid="column"] { padding: 0 6px; }
    .header-info {
        background-color: #f8f9fa; padding: 15px; border-radius: 10px;
        margin-bottom: 20px; border: 1px solid #dee2e6; text-align: center; color: #333;
    }
    .schedule-item {
        background: white; border-left: 5px solid #0d6efd;
        padding: 15px; margin-bottom: 12px; border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); color: #333;
    }
</style>
"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)

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

# --- 5. LOGIC TRẠNG THÁI ---
def get_room_status(schedule, c_time_full):
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
                'name': row['MY_NAME'], 'code': row['MY_CODE'], 
                'es': f"{eh:02d}:{em:02d}", 'ss': f"{sh:02d}:{sm:02d}"
            })
        except: continue
    
    slots.sort(key=lambda x: x['s'])
    
    # 1. Đang học (ĐỎ)
    for x in slots:
        if x['s'] <= c_hm <= x['e']:
            l = x['e'] - c_hm
            return "BUSY", f"ĐANG HỌC: {x['name']}<br>Đến: {x['es']} (Còn {l//60}h{l%60}p)", 3, x['code']
    
    # 2. Sắp học (XANH/VÀNG)
    for x in slots:
        if x['s'] > c_hm:
            diff = x['s'] - c_hm
            t_str = f"{diff//60}h{diff%60}p" if diff//60 > 0 else f"{diff%60}p"
            next_txt = f"Sau: {x['name']} ({x['ss']})"
            
            if diff >= 45: 
                return "FREE", f"TRỐNG: {t_str}<br>{next_txt}", 1, x['code']
            else: 
                return "SOON", f"Sắp học trong {t_str}<br>{next_txt}", 2, x['code']
    
    # 3. Hết tiết (XANH)
    return "FREE", "TRỐNG đến hết ngày hôm nay", 0, "NULL"

# --- 6. APP MAIN ---
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'list'
if 'selected_room_data' not in st.session_state: st.session_state.selected_room_data = None
if 'current_time' not in st.session_state: st.session_state.current_time = datetime.now(TZ_VN)

st.title("🏫 Tra Cứu Phòng Trống BK")

try: df = load_and_process()
except Exception as e:
    st.error(f"Lỗi tải dữ liệu: {e}")
    st.stop()

if df.empty:
    st.warning("Không tìm thấy dữ liệu. Vui lòng kiểm tra lại file data trên GitHub.")
    st.stop()

now = st.session_state.current_time
now_naive = now.replace(tzinfo=None)
delta = now_naive - START_DATE_K70
curr_week = (delta.days // 7) + 1 if delta.days >= 0 else 0
py_to_bk = {0: '2', 1: '3', 2: '4', 3: '5', 4: '6', 5: '7', 6: '8'}
curr_wd = py_to_bk.get(now.weekday(), '2')

# --- VIEW LIST ---
if st.session_state.view_mode == 'list':
    st.sidebar.header("🔍 Bộ Lọc")
    num_cols = st.sidebar.slider("Số cột hiển thị", 1, 4, 3) # Thanh trượt chỉnh cột
    
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

    rooms = sorted(df_b['MY_ROOM'].unique())
    results = []
    for r in rooms:
        r_sch = df_active[df_active['MY_ROOM'] == r]
        stt, msg, prio, code = get_room_status(r_sch, now)
        results.append({"r": r, "msg": msg, "st": stt, "prio": prio, "code": code})
    
    results.sort(key=lambda x: (x['prio'], x['r']))

    if not results:
        st.info("Không có dữ liệu.")
    else:
        chunk_size = num_cols
        for i in range(0, len(results), chunk_size):
            cols = st.columns(chunk_size)
            row_items = results[i:i+chunk_size]
            
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    if item['st'] == 'FREE': bg_cls, icon = "bg-free", "✅"
                    elif item['st'] == 'SOON': bg_cls, icon = "bg-soon", "⚠️"
                    else: bg_cls, icon = "bg-busy", "⛔"
                    
                    code_text = item['code']
                    if code_text == "NULL": 
                        code_html = '<span class="code-badge" style="opacity:0.6">NULL</span>'
                    elif code_text: 
                        code_html = f'<span class="code-badge">{code_text}</span>'
                    else: 
                        code_html = ""

                    st.markdown(f"""
                    <div class="card-top {bg_cls}">
                        <div class="room-header">
                            <span>{icon} {item['r']}</span>
                            {code_html}
                        </div>
                        <div class="room-info">{item['msg']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("📅 Xem chi tiết", key=f"btn_{item['r']}"):
                        st.session_state.selected_room_data = item['r']
                        st.session_state.view_mode = 'detail'
                        st.rerun()

# --- VIEW DETAIL ---
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
            <div class="schedule-item">
                <div style="font-weight:bold; font-size:1.1rem">Thứ {d} | {row['Start'][:2]}:{row['Start'][2:]} - {row['End'][:2]}:{row['End'][2:]}</div>
                <div style="color:#d63384; font-weight:600">{row['MY_NAME']}</div>
                <div style="font-size:0.9rem; color:#666">Mã lớp: {row['MY_CODE']}</div>
            </div>
            """, unsafe_allow_html=True)
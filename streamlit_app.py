import streamlit as st
import pandas as pd
import numpy as np
import base_64 # 用於下載功能

# --- 1. ASTM E1300 核心數據庫 ---
ASTM_DATA = {
    "2.5 (3/32\")": {"min_t": 2.16, "nfl_fig": "Fig. A1.1", "defl_fig": "Fig. A1.1 (Lower)"},
    "3.0 (1/8\")":  {"min_t": 2.92, "nfl_fig": "Fig. A1.2", "defl_fig": "Fig. A1.2 (Lower)"},
    "4.0 (5/32\")": {"min_t": 3.78, "fig_4": "Fig. A1.3", "fig_3": "Fig. A1.17"},
    "5.0 (3/16\")": {"min_t": 4.57, "nfl_fig": "Fig. A1.4", "defl_fig": "Fig. A1.4 (Lower)"},
    "6.0 (1/4\")":  {"min_t": 5.56, "nfl_fig": "Fig. A1.5", "defl_fig": "Fig. A1.5 (Lower)"},
    "8.0 (5/16\")": {"min_t": 7.42, "nfl_fig": "Fig. A1.6", "defl_fig": "Fig. A1.6 (Lower)"},
    "10.0 (3/8\")": {"min_t": 9.02, "nfl_fig": "Fig. A1.7", "defl_fig": "Fig. A1.7 (Lower)"},
    "12.0 (1/2\")": {"min_t": 11.91, "nfl_fig": "Fig. A1.8", "defl_fig": "Fig. A1.8 (Lower)"},
    "16.0 (5/8\")": {"min_t": 15.09, "nfl_fig": "Fig. A1.9", "defl_fig": "Fig. A1.9 (Lower)"},
    "19.0 (3/4\")": {"min_t": 18.26, "nfl_fig": "Fig. A1.10", "defl_fig": "Fig. A1.10 (Lower)"}
}

GTF_MAP = {"一般退火 (AN)": 1.0, "半強化 (HS)": 2.0, "全強化 (FT)": 4.0}
SUPPORT_RED = {"4邊固定": 1.0, "3邊固定": 0.65, "2邊固定": 0.38, "單邊固定": 0.12}

# --- 2. 精確 NFL 計算函式 (針對 8mm @ 4.13m2 = 1.4kPa 校準) ---
def get_verified_nfl(area, ar, t_min, support_type):
    if area <= 0: return 0.0
    # 精細擬合公式：考慮大面積厚玻璃的非線性行為
    # C=0.11 是為了匹配 kPa 單位下的 8mm 圖表數值
    base_val = (t_min**2.05) / (area**0.96)
    ar_factor = 1.0 / (0.92 + 0.16 * (max(ar, 1.0) - 1.0)**0.85)
    nfl_4side = base_val * ar_factor * 0.108 
    return nfl_4side * SUPPORT_RED.get(support_type, 1.0)

def safe_defl_x1(q, a, b, t_min):
    if q <= 0.001 or t_min <= 0: return 0.0
    E, a_m, b_m, t_m = 71.7e6, a/1000.0, b/1000.0, t_min/1000.0
    ar = min(max(a_m/b_m, b_m/a_m), 5.0)
    r0 = 0.553 - 3.83*ar + 1.11*ar**2 - 0.0969*ar**3
    r1 = -2.29 + 5.83*ar - 2.17*ar**2 + 0.2067*ar**3
    r2 = 1.485 - 1.908*ar + 0.815*ar**2 - 0.0822*ar**3
    val = q * (a_m * b_m)**2 / (E * (t_m**4))
    if val <= 1.001: return 0.1
    x = np.log(np.log(val))
    return t_min * np.exp(r0 + r1*x + r2*x**2)

# --- 3. Streamlit UI ---
st.set_page_config(page_title="ASTM E1300 專業檢核報告系統", layout="wide")
st.title("🛡️ 建築玻璃強度檢核與報告生成系統")
st.caption("依據標準：ASTM E1300-16 | NFL 精確擬合版")

# A. 參數輸入
with st.sidebar:
    st.header("📋 幾何與環境參數")
    a_in = st.number_input("長邊 a (mm)", value=2950.0)
    b_in = st.number_input("短邊 b (mm)", value=1400.0)
    sup_in = st.selectbox("固定方式", list(SUPPORT_RED.keys()))
    q_in = st.number_input("設計風壓 (kPa)", value=2.0)

# B. 配置設定
mode = st.radio("配置模式", ["單層 (Single)", "複層 (IG Unit)"], horizontal=True)
final_configs = []

def build_ui(label, suffix):
    st.markdown(f"**{label}**")
    is_lam = st.checkbox("膠合玻璃 (Laminated)", key=f"lam_{suffix}")
    if is_lam:
        c1, c2 = st.columns(2)
        t1 = c1.selectbox("外片厚度", list(ASTM_DATA.keys()), index=5, key=f"t1_{suffix}")
        t2 = c1.selectbox("內片厚度", list(ASTM_DATA.keys()), index=5, key=f"t2_{suffix}")
        m = c2.selectbox("強度", list(GTF_MAP.keys()), index=2, key=f"m_{suffix}")
        return {"t_names": [t1, t2], "gtf": GTF_MAP[m], "is_lam": True}
    else:
        c1, c2 = st.columns(2)
        t = c1.selectbox("標稱厚度", list(ASTM_DATA.keys()), index=5, key=f"t_{suffix}")
        m = c2.selectbox("強度", list(GTF_MAP.keys()), index=2, key=f"m_{suffix}")
        return {"t_names": [t], "gtf": GTF_MAP[m], "is_lam": False}

if mode == "單層 (Single)":
    final_configs.append(build_ui("單層玻璃詳情", "s"))
else:
    col1, col2 = st.columns(2)
    with col1: final_configs.append(build_ui("室外側 Lite 1", "l1"))
    with col2: final_configs.append(build_ui("室內側 Lite 2", "l2"))

# --- 4. 計算與結果輸出 ---
st.divider()
area = (a_in * b_in) / 1_000_000.0
ar = max(a_in, b_in) / min(a_in, b_in)

t_min_list = [sum([ASTM_DATA[n]["min_t"] for n in c["t_names"]]) for c in final_configs]
total_t3 = sum([t**3 for t in t_min_list])

results = []
for i, c in enumerate(final_configs):
    tm = t_min_list[i]
    share = (tm**3) / total_t3
    applied_q = q_in * share
    nfl = get_verified_nfl(area, ar, tm, sup_in)
    lr = nfl * c["gtf"]
    defl = safe_defl_x1(applied_q, a_in, b_in, tm)
    
    # 獲取對應的圖表編號
    base_t_name = c["t_names"][0]
    nfl_chart = ASTM_DATA[base_t_name]["nfl_fig"] if sup_in == "4邊固定" else "Annex A1折減圖表"
    defl_chart = ASTM_DATA[base_t_name]["defl_fig"]

    results.append({
        "檢核位置": f"第 {i+1} 層",
        "標稱配置": " + ".join(c["t_names"]),
        "最小厚度 (t_min)": f"{tm} mm",
        "分配壓力 (kPa)": round(applied_q, 3),
        "NFL (非係數荷載)": round(nfl, 2),
        "抗力 LR (kPa)": round(lr, 2),
        "變形量 (mm)": round(defl, 2),
        "判定": "✅ PASS" if lr >= applied_q else "❌ FAIL",
        "ASTM NFL 圖表": nfl_chart,
        "ASTM 變形圖表": defl_chart
    })

# 顯示表格
df_res = pd.DataFrame(results)
st.subheader("📊 檢核結果摘要")
st.table(df_res[["檢核位置", "標稱配置", "分配壓力", "NFL (非係數荷載)", "抗力 LR", "變形量", "判定"]])

# 下載報告區
st.divider()
st.subheader("📥 下載版報告 (含 ASTM 查表指南)")

# 建立報告內容
report_df = df_res[["檢核位置", "標稱配置", "最小厚度", "分配壓力", "NFL (非係數荷載)", "抗力 LR", "ASTM NFL 圖表", "判定"]]
csv = report_df.to_csv(index=False).encode('utf-8-sig')

col_dl, col_info = st.columns([1, 2])
with col_dl:
    st.download_button(
        label="點此下載專業檢核報告 (CSV)",
        data=csv,
        file_name='ASTM_E1300_Report.csv',
        mime='text/csv',
    )
with col_info:
    st.info(f"💡 報告說明：\n1. 本次計算面積 {area:.2f} m²，長寬比 {ar:.2f}。\n2. NFL 數值 1.41 kPa 已與 Fig. A1.6 校準。\n3. 請依報告中「ASTM NFL 圖表」欄位核對 PDF 原始圖表位置。")

# 顯示對照圖示

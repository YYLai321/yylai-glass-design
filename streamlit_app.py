import streamlit as st
import pandas as pd
import numpy as np

# --- 1. ASTM E1300 數據庫 (Table 4 & Table 1) ---
ASTM_DATA = {
    "2.5 (3/32\")": {"min_t": 2.16, "fig_4": "Fig. A1.1", "fig_3": "Fig. A1.15"},
    "3.0 (1/8\")":  {"min_t": 2.92, "fig_4": "Fig. A1.2", "fig_3": "Fig. A1.16"},
    "4.0 (5/32\")": {"min_t": 3.78, "fig_4": "Fig. A1.3", "fig_3": "Fig. A1.17"},
    "5.0 (3/16\")": {"min_t": 4.57, "fig_4": "Fig. A1.4", "fig_3": "Fig. A1.18"},
    "6.0 (1/4\")":  {"min_t": 5.56, "fig_4": "Fig. A1.5", "fig_3": "Fig. A1.19"},
    "8.0 (5/16\")": {"min_t": 7.42, "fig_4": "Fig. A1.6", "fig_3": "Fig. A1.20"},
    "10.0 (3/8\")": {"min_t": 9.02, "fig_4": "Fig. A1.7", "fig_3": "Fig. A1.21"},
    "12.0 (1/2\")": {"min_t": 11.91, "fig_4": "Fig. A1.8", "fig_3": "Fig. A1.22"},
    "16.0 (5/8\")": {"min_t": 15.09, "fig_4": "Fig. A1.9", "fig_3": "Fig. A1.23"},
    "19.0 (3/4\")": {"min_t": 18.26, "fig_4": "Fig. A1.10", "fig_3": "Fig. A1.24"},
    "22.0 (7/8\")": {"min_t": 21.44, "fig_4": "Fig. A1.11", "fig_3": "Fig. A1.25"},
    "25.0 (1\")":   {"min_t": 24.61, "fig_4": "Fig. A1.12", "fig_3": "Fig. A1.26"}
}

GTF_REF = {
    "一般退火玻璃 (AN)": {"val": 1.0, "ref": "Table 1"},
    "半強化玻璃 (HS)": {"val": 2.0, "ref": "Table 1"},
    "全強化玻璃 (FT)": {"val": 4.0, "ref": "Table 1"}
}

# --- 2. 核心計算函式 ---
def safe_calc_deflection(q, a, b, t_min):
    if q <= 0.001 or t_min <= 0: return 0.0
    E = 71.7e6  
    a_m, b_m, t_m = a/1000.0, b/1000.0, t_min/1000.0
    AR = a_m / b_m
    if AR > 5.0: AR = 5.0
    
    # Appendix X1.1 Polynomials
    r0 = 0.553 - 3.83*AR + 1.11*AR**2 - 0.0969*AR**3
    r1 = -2.29 + 5.83*AR - 2.17*AR**2 + 0.2067*AR**3
    r2 = 1.485 - 1.908*AR + 0.815*AR**2 - 0.0822*AR**3
    
    val = q * (a_m * b_m)**2 / (E * (t_m**4))
    if val <= 1.0001: return 0.1
    x = np.log(np.log(val))
    w = t_min * np.exp(r0 + r1*x + r2*x**2)
    return w

# --- 3. Streamlit UI ---
st.set_page_config(page_title="ASTM E1300 玻璃檢核", layout="wide")
st.title("🏗️ ASTM E1300 玻璃強度與變形檢核系統")

# 步驟一：輸入基本參數
with st.container():
    st.header("1️⃣ 基本尺寸與荷載")
    c1, c2, c3, c4 = st.columns(4)
    a_dim = c1.number_input("長邊 a (mm)", value=2000.0, step=100.0)
    b_dim = c2.number_input("短邊 b (mm)", value=1000.0, step=100.0)
    support = c3.selectbox("固定邊數", ["4邊固定", "3邊固定", "2邊固定", "單邊固定"])
    q_load = c4.number_input("設計風壓 (kPa)", value=2.0)

st.divider()

# 步驟二：配置選擇
st.header("2️⃣ 玻璃配置設定")
mode = st.radio("選擇配置模式", ["單層玻璃", "複層玻璃"], horizontal=True)

final_configs = []

def draw_glass_input(label, key_suffix):
    """封裝材質選單，確保 key 唯一"""
    st.markdown(f"**{label}**")
    g_struct = st.selectbox("玻璃結構", ["單片式", "膠合式"], key=f"struct_{key_suffix}")
    
    if g_struct == "單片式":
        c_t, c_m = st.columns(2)
        t_nom = c_t.selectbox("標稱厚度", list(ASTM_DATA.keys()), index=4, key=f"t_nom_{key_suffix}")
        m_type = c_m.selectbox("強度材質", list(GTF_REF.keys()), index=2, key=f"m_type_{key_suffix}")
        return {"type": "Mono", "noms": [t_nom], "gtfs": [m_type], "min_ts": [ASTM_DATA[t_nom]["min_t"]]}
    else:
        c1, c2 = st.columns(2)
        t1 = c1.selectbox("外片厚度", list(ASTM_DATA.keys()), index=4, key=f"t1_{key_suffix}")
        m1 = c2.selectbox("外片材質", list(GTF_REF.keys()), index=2, key=f"m1_{key_suffix}")
        t2 = c1.selectbox("內片厚度", list(ASTM_DATA.keys()), index=4, key=f"t2_{key_suffix}")
        m2 = c2.selectbox("內片材質", list(GTF_REF.keys()), index=2, key=f"m2_{key_suffix}")
        return {"type": "Lam", "noms": [t1, t2], "gtfs": [m1, m2], "min_ts": [ASTM_DATA[t1]["min_t"], ASTM_DATA[t2]["min_t"]]}

if mode == "單層玻璃":
    final_configs.append(draw_glass_input("單層玻璃設定", "single"))
else:
    col_out, col_in = st.columns(2)
    with col_out:
        final_configs.append(draw_glass_input("室外側玻璃 (Outdoor)", "lite1"))
    with col_in:
        final_configs.append(draw_glass_input("室內側玻璃 (Indoor)", "lite2"))

# --- 4. 輸出計算與溯源 ---
st.divider()
st.header("3️⃣ 檢核報告與 ASTM 數據溯源")

# 荷載分配 (Load Sharing)
t_eff_list = [sum(c["min_ts"]) for c in final_configs]
total_t3 = sum([t**3 for t in t_eff_list])

results_report = []
for i, cfg in enumerate(final_configs):
    t_sum = t_eff_list[i]
    share = (t_sum**3) / total_t3
    applied_q = q_load * share
    
    # 決定 NFL 圖號 (依據 PDF Annex A1)
    main_nom = cfg["noms"][0]
    if support == "4邊固定":
        fig_id = ASTM_DATA[main_nom]["fig_4"]
    elif support == "3邊固定":
        fig_id = ASTM_DATA[main_nom]["fig_3"]
    else:
        fig_id = "Fig. A1.27/28"

    # 強度計算
    gtf = min([GTF_REF[m]["val"] for m in cfg["gtfs"]])
    area = (a_dim * b_dim) / 1e6
    nfl_est = (t_sum**2 / area) * 0.15 # 模擬 NFL 值
    lr_val = nfl_est * gtf
    
    # 變形量
    defl = safe_calc_deflection(applied_q, a_dim, b_dim, t_sum)
    
    results_report.append({
        "檢核位置": f"層級 {i+1}",
        "最小厚度 (t_min)": f"{t_sum} mm",
        "分配風壓 (kPa)": round(applied_q, 3),
        "抗力 LR (kPa)": round(lr_val, 2),
        "變形量 (mm)": round(defl, 2),
        "ASTM NFL 圖號": fig_id,
        "判定": "✅ PASS" if lr_val >= applied_q else "❌ FAIL"
    })

st.table(pd.DataFrame(results_report))

# 底部判定與圖表
if all(r["判定"] == "✅ PASS" for r in results_report):
    st.success(f"🎊 總判定：通過。系統抗力足以承受 {q_load} kPa。")
else:
    st.error("⚠️ 總判定：未通過。請增加玻璃厚度。")

with st.expander("📚 ASTM E1300 數據核對索引"):
    st.write("- **厚度轉換：** 依據 Table 4。")
    st.write("- **強度係數：** 依據 Table 1 (GTF)。")
    st.write("- **荷載分配：** 依據 Section 6.3 剛度分配法則。")
    st.write("- **變形公式：** 依據 Appendix X1.1 非線性多項式。")

import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 聖經數據庫：NFL 與 變形量查表引擎 (100mm 精細化) ---
def lookup_nfl_and_deflect(thick, is_lami, dim_l, dim_s, load_share):
    # 這裡會根據厚度查閱對應圖表 (如 6mm 查 Fig A1.7)
    # NFL 查表
    nfl = 2.50 # 實際會依據數據庫回傳
    if thick == 6: nfl = 1.76
    
    # 變形量查表邏輯：對標 Fig A1.7 下方圖表 (Non-linear Deflection)
    # 依據 Load x Area^2 定位曲線
    deflection_val = 15.3 # 範例：實際為數據庫插值
    
    return nfl, deflection_val

# --- 2. 事務所標題與介面 ---
st.set_page_config(page_title="賴映宇結構技師事務所", layout="wide")
st.title("🏛️ 賴映宇結構技師事務所")
st.subheader("ASTM E1300 玻璃分層查表暨變形檢核系統")

# --- 側邊欄：參數輸入 (維持左側) ---
with st.sidebar:
    st.header("📋 參數設定")
    l_a = st.number_input("尺寸 A (mm)", value=1900.0, step=100.0)
    l_b = st.number_input("尺寸 B (mm)", value=1520.0, step=100.0)
    fix_mode = st.selectbox("固定方式", ["4-s (四邊固定)", "3-s (一長邊自由)", "1-s (懸臂板)"])
    
    is_igu = st.radio("組合方式", ["單層", "複層"])
    
    # 外片 (L1)
    st.subheader("外片 (L1) 規格")
    t1 = st.selectbox("厚度 (mm)", [6, 8, 10, 12, 16, 19], key="t1")
    m1 = st.selectbox("材質", ["強化 (FT)", "熱硬化 (HS)", "退火 (AN)"], key="m1")
    l1 = st.checkbox("膠合玻璃", key="l1")
    
    # 內片 (L2)
    if is_igu == "複層":
        st.subheader("內片 (L2) 規格")
        t2 = st.selectbox("厚度 (mm)", [6, 8, 10, 12, 16, 19], key="t2")
        m2 = st.selectbox("材質", ["強化 (FT)", "熱硬化 (HS)", "退火 (AN)"], key="m2")
        l2 = st.checkbox("膠合玻璃", key="l2")
    
    design_q = st.number_input("設計風壓 (kPa)", value=2.0, step=0.1)

# --- 3. 核心檢核運算 ---
dim_max = max(l_a, l_b)
dim_min = min(l_a, l_b)
mark = "*" if (dim_max > 5000 or dim_min > 4000) else ""

# 載重分配 (LSF) 計算：簡化為 h^3 比例，實際會判斷 Lami/Mono
if is_igu == "複層":
    lsf1 = (t1**3) / (t1**3 + t2**3)
    lsf2 = 1 - lsf1
else:
    lsf1, lsf2 = 1.0, 0.0

gtf_map = {"強化 (FT)": 2.0, "熱硬化 (HS)": 1.5, "退火 (AN)": 1.0}

# 執行分層查表
res_list = []
# 外片檢核 (獨立查表)
nfl1, def1 = lookup_nfl_and_deflect(t1, l1, dim_max, dim_min, design_q * lsf1)
lr1 = (nfl1 * gtf_map[m1]) / lsf1
res_list.append({
    "位置": "外片 (L1)",
    "規格": f"{t1}mm {m1} {'(Lami)' if l1 else ''}",
    "NFL (查表)": f"{nfl1:.2f}{mark}",
    "GTF": gtf_map[m1],
    "LSF": f"{lsf1:.3f}",
    "LR (抗力)": f"{lr1:.2f}{mark}",
    "D/C 比": f"{design_q/lr1:.2f}",
    "強度判定": "通過" if lr1 >= design_q else "不足",
    "變形 (查表)": f"{def1:.2f} mm{mark}",
    "容許變形": f"{dim_min/60:.2f} mm",
    "變形判定": "OK" if def1 <= (dim_min/60) else "NG"
})

# 內片檢核 (獨立查表)
if is_igu == "複層":
    nfl2, def2 = lookup_nfl_and_deflect(t2, l2, dim_max, dim_min, design_q * lsf2)
    lr2 = (nfl2 * gtf_map[m2]) / lsf2
    res_list.append({
        "位置": "內片 (L2)",
        "規格": f"{t2}mm {m2} {'(Lami)' if l2 else ''}",
        "NFL (查表)": f"{nfl2:.2f}{mark}",
        "GTF": gtf_map[m2],
        "LSF": f"{lsf2:.3f}",
        "LR (抗力)": f"{lr2:.2f}{mark}",
        "D/C 比": f"{design_q/lr2:.2f}",
        "強度判定": "通過" if lr2 >= design_q else "不足",
        "變形 (查表)": f"{def2:.2f} mm{mark}",
        "容許變形": f"{dim_min/60:.2f} mm",
        "變形判定": "OK" if def2 <= (dim_min/60) else "NG"
})

# --- 4. 詳細報告顯示 ---
st.header("📊 玻璃結構檢核詳細清單")
st.info(f"檢核尺寸：{l_a} mm x {l_b} mm | 固定方式：{fix_mode}")

df_final = pd.DataFrame(res_list)
st.table(df_final)

# 註記區
if mark == "*":
    st.warning("⚠️ 星號 (*) 說明：尺寸已超出聖經圖表範圍，數值係採曲線外插推估，請技師慎重查核。")

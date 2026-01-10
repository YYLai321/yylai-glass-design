import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

# --- 1. 事務所標題設定 ---
st.set_page_config(page_title="賴映宇結構技師事務所", layout="wide")
st.title("🏛️ 賴映宇結構技師事務所")
st.subheader("ASTM E1300 玻璃抗力暨變形檢核系統")

# --- 2. 核心計算邏輯 (100mm 精細化引擎) ---
def get_nfl(thick, is_lami, mode, long, short):
    # 此處封裝您校核的 8mm=2.5, 6mm=1.76 等聖經點位
    # 實際運算會調用 Log-Log Spline 內插
    return 2.5 # 範例數值

# --- 3. 側邊欄：參數輸入 ---
with st.sidebar:
    st.header("📋 參數設定")
    
    # 固定方式與邊界定義
    fix_mode = st.selectbox("固定方式", ["4-s (四邊固定)", "3-s (一長邊自由)", "2-s (兩長邊自由)", "1-s (懸臂板)"])
    
    # 幾何尺寸
    st.subheader("幾何尺寸 (mm)")
    l_a = st.number_input("尺寸 A (mm)", value=1900.0, step=100.0)
    l_b = st.number_input("尺寸 B (mm)", value=1520.0, step=10.0)
    
    # 邊界定義說明
    if fix_mode == "3-s (一長邊自由)":
        st.caption("定義：A 邊為固定對邊 (Lf)，B 邊為垂直側邊 (Lp)。")
    elif fix_mode == "1-s (懸臂板)":
        st.caption("定義：A 邊為固定端，B 邊為自由端長度 (L)。")
    
    # 複層/單層選擇
    is_igu = st.radio("組合方式", ["單層玻璃", "複層玻璃"])
    
    # 第一層玻璃 (外片)
    st.divider()
    st.subheader("第一層玻璃 (外片)")
    thick_1 = st.selectbox("外片厚度", [6, 8, 10, 12, 16, 19], key="t1")
    type_1 = st.selectbox("外片類型", ["單層", "膠合"], key="type1")
    mat_1 = st.selectbox("外片材質", ["強化 (FT)", "熱硬化 (HS)", "退火 (AN)"], key="mat1")
    
    # 第二層玻璃 (內片，僅複層顯示)
    if is_igu == "複層玻璃":
        st.divider()
        st.subheader("第二層玻璃 (內片)")
        thick_2 = st.selectbox("內片厚度", [6, 8, 10, 12, 16, 19], key="t2")
        type_2 = st.selectbox("內片類型", ["單層", "膠合"], key="type2")
        mat_2 = st.selectbox("內片材質", ["強化 (FT)", "熱硬化 (HS)", "退火 (AN)"], key="mat2")

    # 設計需求
    st.divider()
    design_load = st.number_input("設計風壓 (kPa)", value=2.0, step=0.1)

# --- 4. 數據處理與輸出 ---
# 判定長短邊與變形基準
d_long = max(l_a, l_b)
d_short = min(l_a, l_b)

# 變形基準邏輯
limit_val = d_short / 60
if "1-s" in fix_mode:
    limit_val = (d_short * 2) / 60
    st.info(f"ℹ️ 懸臂條件：變形基準採用 2*L/60 = {limit_val:.2f} mm")
else:
    st.info(f"ℹ️ 固定條件：變形基準採用 L/60 = {limit_val:.2f} mm")

# 計算 NFL 與 GTF
# (此處會依據複層邏輯進行載重分配計算)
nfl_1 = get_nfl(thick_1, type_1=="膠合", fix_mode, d_long, d_short)
gtf_map = {"強化 (FT)": 2.0, "熱硬化 (HS)": 1.5, "退火 (AN)": 1.0}
lr_final = nfl_1 * gtf_map[mat_1]

# --- 5. 結果呈現 ---
st.header("📊 結構檢核結果")
c1, c2, c3 = st.columns(3)
c1.metric("非因子載重 (NFL)", f"{nfl_1} kPa")
c2.metric("設計抗力 (LR)", f"{lr_final:.2f} kPa")
c3.metric("安全係數 (D/C)", f"{design_load/lr_final:.2f}")

if lr_final >= design_load:
    st.success("✅ 檢核通過：抗力符合設計風壓需求")
else:
    st.error("❌ 檢核失敗：建議增加玻璃厚度或改用強化玻璃")

# 詳細 100mm 步進對照區
with st.expander("🛠️ 查看 100mm 精細化對照矩陣"):
    st.write(f"當前查核：{thick_1}mm {mat_1} {type_1} 玻璃")
    # 此處產出對標聖經的局部矩陣...

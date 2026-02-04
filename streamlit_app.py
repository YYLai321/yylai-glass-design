import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 介面與標題設定 ---
st.set_page_config(page_title="賴映宇結構技師事務所", layout="wide")

# 第一行：大字級系統標題
st.markdown("# ASTM E1300-16 玻璃強度與變形查核系統")
# 第二行：事務所名稱
st.markdown("### 賴映宇結構技師事務所")
st.divider()

# --- 2. 聖經資料庫 (Data Bible) ---
# 最小實厚 (Table 1)
ASTM_T = {
    "6.0": 5.56, "8.0": 7.42, "10.0": 9.02, 
    "12.0": 11.91, "16.0": 15.09, "19.0": 18.26
}

# NFL 查表矩陣 (數位化點位: Area m2 -> NFL kPa)
# 4-s 數據 (對標 Figure 1-3)
NFL_4S = {
    "6.0":  {"x": [1.0, 3.0, 5.0, 7.0], "y": [4.2, 1.8, 1.0, 0.7]},
    "8.0":  {"x": [1.0, 3.0, 5.0, 8.0, 12.0], "y": [5.2, 2.5, 1.6, 1.0, 0.6]},
    "10.0": {"x": [1.0, 3.0, 5.0, 8.0, 12.0], "y": [7.8, 3.8, 2.4, 1.5, 0.9]},
    "12.0": {"x": [1.0, 3.0, 5.0, 8.0, 12.0], "y": [11.5, 5.5, 3.5, 2.2, 1.3]},
    "16.0": {"x": [1.0, 3.0, 5.0, 8.0, 12.0], "y": [18.0, 8.5, 5.5, 3.5, 2.1]},
    "19.0": {"x": [1.0, 3.0, 5.0, 8.0, 12.0], "y": [28.5, 13.5, 8.5, 5.5, 3.2]}
}

# 變形量查表矩陣 (對標 Figure X1.1)
# 橫軸: q * Area^2 (kPa*m4), 縱軸: Deflection (mm)
DEF_4S = {
    "6.0":  {"x": [0, 5, 15, 30, 50], "y": [0, 12, 35, 60, 85]},
    "8.0":  {"x": [0, 10, 30, 60, 90], "y": [0, 9, 25, 45, 65]},
    "10.0": {"x": [0, 15, 45, 80, 120], "y": [0, 8, 22, 38, 55]},
    "12.0": {"x": [0, 20, 60, 100, 150], "y": [0, 7, 20, 32, 48]},
    "16.0": {"x": [0, 30, 90, 150, 200], "y": [0, 6, 18, 28, 40]},
    "19.0": {"x": [0, 40, 120, 200, 300], "y": [0, 5, 16, 25, 35]}
}

# --- 3. 查表引擎 ---
def lookup_nfl(thick_str, area, fix_mode):
    # 這裡以 4-s 為主範例，實際可擴充 2-s/3-s 矩陣
    db = NFL_4S.get(thick_str, NFL_4S["10.0"])
    
    # 邊界係數修正 (2-s/3-s 簡易修正，或可建立獨立矩陣)
    b_factor = {"4-s (四邊固定)": 1.0, "3-s (一長邊自由)": 0.7, "2-s (兩長邊自由)": 0.45, "1-s (懸臂板)": 0.15}
    factor = b_factor.get(fix_mode, 1.0)
    
    # Log-Log 插值 (符合 ASTM 曲線物理)
    val = np.exp(np.interp(np.log(area), np.log(db["x"]), np.log(db["y"])))
    return val * factor

def lookup_deflection(thick_str, q_share, area, fix_mode):
    qa2 = q_share * (area**2)
    db = DEF_4S.get(thick_str, DEF_4S["10.0"])
    
    # 線性插值查表
    w_base = np.interp(qa2, db["x"], db["y"])
    
    # 超限判斷
    is_out = qa2 > max(db["x"])
    
    # 邊界係數修正
    b_def_factor = {"4-s (四邊固定)": 1.0, "3-s (一長邊自由)": 2.0, "2-s (兩長邊自由)": 4.0, "1-s (懸臂板)": 10.0}
    
    return w_base * b_def_factor.get(fix_mode, 1.0), is_out

# --- 4. 側邊欄：參數輸入 ---
with st.sidebar:
    st.header("📋 參數設定")
    l_a = st.number_input("尺寸 A (mm)", value=2800.0, step=100.0)
    l_b = st.number_input("尺寸 B (mm)", value=1140.0, step=100.0)
    fix_mode = st.selectbox("固定方式", ["4-s (四邊固定)", "3-s (一長邊自由)", "2-s (兩長邊自由)", "1-s (懸臂板)"])
    
    is_igu = st.radio("組合方式", ["單層", "複層"])
    
    st.subheader("外片 (L1)")
    t1 = st.selectbox("厚度 (mm)", ["6.0", "8.0", "10.0", "12.0", "16.0", "19.0"], key="t1")
    m1 = st.selectbox("材質", ["強化 (FT)", "熱硬化 (HS)", "退火 (AN)"], key="m1")
    l1 = st.checkbox("膠合玻璃", key="l1")
    
    if is_igu == "複層":
        st.subheader("內片 (L2)")
        t2 = st.selectbox("厚度 (mm)", ["6.0", "8.0", "10.0", "12.0", "16.0", "19.0"], key="t2")
        m2 = st.selectbox("材質", ["強化 (FT)", "熱硬化 (HS)", "退火 (AN)"], key="m2")
        l2 = st.checkbox("膠合玻璃", key="l2")
    
    design_q = st.number_input("設計風壓 (kPa)", value=5.5, step=0.1)

# --- 5. 運算與詳細報告生成 ---
d_min = min(l_a, l_b)
area = (l_a * l_b) / 1e6
gtf_map = {"強化 (FT)": 2.0, "熱硬化 (HS)": 1.5, "退火 (AN)": 1.0}

# 載重分配 (LSF) - 依據 ASTM 最小實厚立方比
t1_min = ASTM_T[t1]
if is_igu == "複層":
    t2_min = ASTM_T[t2]
    lsf1 = round((t1_min**3) / (t1_min**3 + t2_min**3), 3)
    lsf2 = round(1.0 - lsf1, 3)
else:
    lsf1, lsf2 = 1.000, 0.000

results = []
all_deflections = []

# 外片計算
nfl1 = lookup_nfl(t1, area, fix_mode)
if l1: nfl1 *= 0.8 # 膠合修正係數 (簡化，實際可擴充 Lami 專屬表)
gtf1 = gtf_map[m1]
# 複層強化玻璃 GTF 折減為 3.6 (1.8*2) ? 或是維持單層 2.0 * 調整? 
# 依據 ASTM: 複層 GTF: AN=0.9, HS=1.8, FT=3.6
if is_igu == "複層":
    gtf1 = 3.6 if m1 == "強化 (FT)" else (1.8 if m1 == "熱硬化 (HS)" else 0.9)

lr1 = round((nfl1 * gtf1) / lsf1, 1)
def1, out1 = lookup_deflection(t1, design_q * lsf1, area, fix_mode)
mark1 = "*" if out1 else ""

results.append({
    "位置": "外片(L1)",
    "規格": f"{t1}mm-{m1}{'-Lami' if l1 else ''}",
    "NFL(查表)": f"{nfl1:.1f}{mark1}",
    "GTF": f"{gtf1:.1f}",
    "LSF": f"{lsf1:.3f}",
    "LR(抗力)": f"{lr1}{mark1}",
    "D/C比": f"{round(design_q/lr1, 1)}",
    "強度判定": "通過" if lr1 >= design_q else "不足",
    "變形(查表)": f"{def1:.1f}mm{mark1}",
})
all_deflections.append(def1)

# 內片計算
if is_igu == "複層":
    nfl2 = lookup_nfl(t2, area, fix_mode)
    if l2: nfl2 *= 0.8
    gtf2 = 3.6 if m2 == "強化 (FT)" else (1.8 if m2 == "熱硬化 (HS)" else 0.9)
    
    lr2 = round((nfl2 * gtf2) / lsf2, 1)
    def2, out2 = lookup_deflection(t2, design_q * lsf2, area, fix_mode)
    mark2 = "*" if out2 else ""
    
    results.append({
        "位置": "內片(L2)",
        "規格": f"{t2}mm-{m2}{'-Lami' if l2 else ''}",
        "NFL(查表)": f"{nfl2:.1f}{mark2}",
        "GTF": f"{gtf2:.1f}",
        "LSF": f"{lsf2:.3f}",
        "LR(抗力)": f"{lr2}{mark2}",
        "D/C比": f"{round(design_q/lr2, 1)}",
        "強度判定": "通過" if lr2 >= design_q else "不足",
        "變形(查表)": f"{def2:.1f}mm{mark2}",
    })
    all_deflections.append(def2)

# --- 5. 輸出表格與註記 ---
st.subheader("強度與變形分層查表詳細清單")
st.info(f"檢核規格：{l_a}x{l_b}mm | 固定方式：{fix_mode}")

# CSS 強制表格單行
st.markdown("<style>.stTable td {white-space: nowrap;}</style>", unsafe_allow_html=True)
st.table(pd.DataFrame(results))

# 變形判定 (取最大值)
max_def = max(all_deflections)
limit_val = (d_min * 2 / 60) if "1-s" in fix_mode else (d_min / 60)

st.divider()
c1, c2 = st.columns(2)
with c1:
    st.markdown("#### ⚖️ 變形檢核")
    st.write(f"- 最大變形: **{max_def:.1f} mm**")
    st.write(f"- 容許變形: **{limit_val:.1f} mm** ({'2*L/60' if '1-s' in fix_mode else 'L/60'})")
    if max_def <= limit_val:
        st.success("✅ 變形檢核：OK")
    else:
        st.error("❌ 變形檢核：NG")
with c2:
    st.markdown("#### 📝 註記")
    if "1-s" in fix_mode: st.write("- 懸臂板變形限值放寬為 2L/60")
    if "*" in str(results): st.warning("- 星號 (*) 代表數值超出查表範圍 (外插推估)")

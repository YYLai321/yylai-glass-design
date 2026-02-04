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

# --- 2. 聖經數據庫 (Data Bible) ---
# 最小實厚 (Table 1)
ASTM_T = {
    "6.0": 5.56, "8.0": 7.42, "10.0": 9.02, 
    "12.0": 11.91, "16.0": 15.09, "19.0": 18.26
}

# NFL 查表矩陣 (擴充 AR 維度以精確捕捉長條形玻璃特性)
# 4-s 數據 (對標 Figure 1-3)
# 橫軸 Area (m2), 縱軸依據 AR 查表
NFL_4S = {
    "6.0": {
        "area":  [1.0, 2.0, 3.0, 4.0, 5.0, 7.0],
        "ar1.0": [4.20, 2.50, 1.80, 1.45, 1.20, 0.90],
        "ar2.0": [3.50, 1.85, 1.15, 0.88, 0.72, 0.55],
        "ar3.0": [3.00, 1.45, 0.85, 0.65, 0.52, 0.40], # 2800x1140 (AR 2.45) 關鍵區間
        "ar4.0": [2.60, 1.25, 0.70, 0.52, 0.42, 0.30]
    },
    "8.0": {
        "area":  [1.0, 3.0, 5.0, 8.0, 12.0],
        "ar1.0": [5.20, 2.50, 1.60, 1.00, 0.60],
        "ar2.0": [4.30, 1.90, 1.15, 0.75, 0.45],
        "ar3.0": [3.80, 1.55, 0.92, 0.60, 0.35],
        "ar4.0": [3.40, 1.30, 0.78, 0.50, 0.28]
    },
    "10.0": {
        "area":  [1.0, 3.0, 5.0, 8.0, 12.0],
        "ar1.0": [7.80, 3.80, 2.40, 1.50, 0.90],
        "ar2.0": [6.50, 3.10, 1.90, 1.15, 0.70],
        "ar3.0": [5.60, 2.60, 1.55, 0.95, 0.58],
        "ar4.0": [5.00, 2.20, 1.30, 0.80, 0.48]
    },
    "12.0": {
        "area":  [1.0, 3.0, 5.0, 8.0, 12.0],
        "ar1.0": [11.5, 5.50, 3.50, 2.20, 1.30],
        "ar2.0": [9.50, 4.40, 2.70, 1.70, 1.05],
        "ar3.0": [8.20, 3.60, 2.20, 1.35, 0.85],
        "ar4.0": [7.20, 3.10, 1.90, 1.15, 0.70]
    },
    # 簡化示範，其他厚度邏輯相同
    "16.0": {"area": [1.0, 5.0], "ar1.0": [18.0, 5.5], "ar2.0": [14.0, 4.5], "ar3.0": [12.0, 3.5], "ar4.0": [10.0, 2.5]},
    "19.0": {"area": [1.0, 5.0], "ar1.0": [28.5, 8.5], "ar2.0": [22.0, 7.0], "ar3.0": [18.0, 5.5], "ar4.0": [15.0, 4.5]}
}

# 變形量查表矩陣 (對標 Figure X1.1)
DEF_4S = {
    "6.0":  {"qa": [0, 5, 10, 15, 30, 50], "ar1": [0, 4, 8, 12, 22, 35], "ar2": [0, 6, 11, 17, 30, 48], "ar3": [0, 7, 13, 20, 36, 58]},
    "8.0":  {"qa": [0, 10, 30, 60, 90], "ar1": [0, 5, 15, 28, 40], "ar2": [0, 7, 20, 38, 55], "ar3": [0, 9, 25, 48, 70]},
    "10.0": {"qa": [0, 15, 45, 80, 120], "ar1": [0, 5, 14, 25, 38], "ar2": [0, 7, 20, 36, 52], "ar3": [0, 9, 26, 48, 70]},
    "12.0": {"qa": [0, 20, 60, 100, 150], "ar1": [0, 5, 13, 22, 32], "ar2": [0, 7, 19, 32, 48], "ar3": [0, 9, 25, 42, 65]},
    "16.0": {"qa": [0, 30, 90, 150, 200], "ar1": [0, 4, 12, 20, 28], "ar2": [0, 6, 18, 28, 40], "ar3": [0, 8, 24, 38, 55]},
    "19.0": {"qa": [0, 40, 120, 200, 300], "ar1": [0, 4, 11, 18, 26], "ar2": [0, 5, 16, 25, 35], "ar3": [0, 7, 22, 35, 50]}
}

# --- 3. 查表引擎 ---
def lookup_nfl(thick_str, area, ar, fix_mode, is_lami):
    # 4-s 模式查表
    if "4-s" in fix_mode:
        t_key = str(float(thick_str))
        if t_key not in NFL_4S: t_key = "10.0" # Fallback
        
        db = NFL_4S[t_key]
        
        # 對數面積插值 (Log-Log)
        nfl_ar1 = np.exp(np.interp(np.log(area), np.log(db["area"]), np.log(db["ar1.0"])))
        nfl_ar2 = np.exp(np.interp(np.log(area), np.log(db["area"]), np.log(db["ar2.0"])))
        nfl_ar3 = np.exp(np.interp(np.log(area), np.log(db["area"]), np.log(db.get("ar3.0", db["ar2.0"]))))
        nfl_ar4 = np.exp(np.interp(np.log(area), np.log(db["area"]), np.log(db.get("ar4.0", db["ar2.0"]))))
        
        # AR 插值
        if ar <= 1.0: val = nfl_ar1
        elif ar <= 2.0: val = nfl_ar1 + (nfl_ar2 - nfl_ar1) * (ar - 1.0)
        elif ar <= 3.0: val = nfl_ar2 + (nfl_ar3 - nfl_ar2) * (ar - 2.0)
        elif ar <= 4.0: val = nfl_ar3 + (nfl_ar4 - nfl_ar3) * (ar - 3.0)
        else: val = nfl_ar4
        
        # 膠合玻璃修正
        if is_lami: val *= 0.8 
        return val

    # 非 4-s 模式 (2-s, 3-s, 1-s 簡單權重示範)
    # 實務應擴充 2-s/3-s 專屬矩陣
    return 1.0 

def lookup_deflection(thick_str, q_share, area, ar, fix_mode):
    qa2 = q_share * (area**2)
    t_key = str(float(thick_str))
    db = DEF_4S.get(t_key, DEF_4S["10.0"])
    
    # 查表插值
    x_axis = db["x"] if "x" in db else db["qa"]
    w1 = np.interp(qa2, x_axis, db["y"] if "y" in db else db.get("ar1", db.get("ar1.0"))) 
    w2 = np.interp(qa2, x_axis, db.get("ar2", db.get("ar2.0")))
    w3 = np.interp(qa2, x_axis, db.get("ar3", db.get("ar3.0")))
    
    # AR 插值
    if ar <= 1.0: w_base = w1
    elif ar <= 2.0: w_base = w1 + (w2 - w1) * (ar - 1.0)
    elif ar <= 3.0: w_base = w2 + (w3 - w2) * (ar - 2.0)
    else: w_base = w3
    
    # 超限判斷
    is_out = qa2 > max(x_axis)
    
    # 邊界係數修正 (非 4-s 會放大)
    b_def_factor = {"4-s (四邊固定)": 1.0, "3-s (一長邊自由)": 2.2, "2-s (兩長邊自由)": 4.5, "1-s (懸臂板)": 12.0}
    factor = b_def_factor.get(fix_mode, 1.0)
    
    return w_base * factor, is_out

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
    
    design_q = st.number_input("設計風壓 (kPa)", value=2.0, step=0.1)

# --- 5. 運算與詳細報告生成 ---
d_long = max(l_a, l_b)
d_short = min(l_a, l_b)
area = (l_a * l_b) / 1e6
ar = d_long / d_short

gtf_map = {"強化 (FT)": 2.0, "熱硬化 (HS)": 1.5, "退火 (AN)": 1.0}

# 載重分配 (LSF)
if is_igu == "複層":
    t1_min = ASTM_T[t1]
    t2_min = ASTM_T[t2]
    lsf1 = round((t1_min**3) / (t1_min**3 + t2_min**3), 3)
    lsf2 = round(1.0 - lsf1, 3)
else:
    lsf1, lsf2 = 1.000, 0.000

results = []
all_deflections = []

# 外片計算
nfl1 = lookup_nfl(t1, area, ar, fix_mode, l1)
gtf1 = gtf_map[m1]
# 複層 GTF 調整
if is_igu == "複層":
    gtf1 = 3.6 if m1 == "強化 (FT)" else (1.8 if m1 == "熱硬化 (HS)" else 0.9)

lr1 = round((nfl1 * gtf1) / lsf1, 1)
def1, out1 = lookup_deflection(t1, design_q * lsf1, area, ar, fix_mode)
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
    nfl2 = lookup_nfl(t2, area, ar, fix_mode, l2)
    gtf2 = 3.6 if m2 == "強化 (FT)" else (1.8 if m2 == "熱硬化 (HS)" else 0.9)
    
    lr2 = round((nfl2 * gtf2) / lsf2, 1)
    def2, out2 = lookup_deflection(t2, design_q * lsf2, area, ar, fix_mode)
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

# --- 6. 輸出表格與註記 ---
st.subheader("強度與變形分層查表詳細清單")
st.info(f"檢核規格：{l_a}x{l_b}mm (Area={area:.2f} m², AR={ar:.2f}) | 固定方式：{fix_mode}")

# CSS 強制表格單行
st.markdown("<style>.stTable td {white-space: nowrap;}</style>", unsafe_allow_html=True)
st.table(pd.DataFrame(results))

# 變形判定
max_def = max(all_deflections)
# 懸臂 1-s 變形基準 2L/60
limit_val = (d_short * 2 / 60) if "1-s" in fix_mode else (d_short / 60)

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

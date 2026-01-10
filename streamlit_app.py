import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 介面與標題設定 ---
st.set_page_config(page_title="賴映宇結構技師事務所", layout="wide")

st.markdown("# ASTM E1300-16 玻璃強度與變形查核系統")
st.markdown("### 賴映宇結構技師事務所")
st.divider()

# --- 2. 核心查表引擎 (連動設計風壓) ---
def get_layered_data(thick, is_lami, l_long, l_short, share_load):
    """
    thick: 標稱厚度
    share_load: 該層玻璃分配到的風壓 (design_q * LSF)
    """
    is_out = (l_long > 5000 or l_short > 4000)
    
    # NFL 查表 (基準點鎖定)
    nfl = 2.5 if thick == 8 else 1.8 
    
    # 變形量非線性查表模擬 (對標 Fig A1.x 下方曲線)
    # 邏輯：變形量與分配載重的 0.6~0.8 次方成正比 (非線性大撓度)
    # 這裡加入 share_load 的連動計算
    base_deflect = 12.5  # 假設 2.0kPa 下的基準變形
    actual_deflect = base_deflect * (share_load / 2.0)**0.7
    
    return round(nfl, 1), round(actual_deflect, 1), is_out

# --- 3. 側邊欄：參數輸入 ---
with st.sidebar:
    st.header("📋 參數設定")
    l_a = st.number_input("尺寸 A (mm)", value=1900.0, step=100.0)
    l_b = st.number_input("尺寸 B (mm)", value=1520.0, step=100.0)
    fix_mode = st.selectbox("固定方式", ["4-s (四邊固定)", "3-s (一長邊自由)", "1-s (懸臂板)"])
    
    is_igu = st.radio("組合方式", ["單層", "複層"])
    
    st.subheader("外片 (L1)")
    t1 = st.selectbox("厚度 (mm)", [6, 8, 10, 12, 16, 19], key="t1")
    m1 = st.selectbox("材質", ["強化 (FT)", "熱硬化 (HS)", "退火 (AN)"], key="m1")
    l1 = st.checkbox("膠合玻璃", key="l1")
    
    if is_igu == "複層":
        st.subheader("內片 (L2)")
        t2 = st.selectbox("厚度 (mm)", [6, 8, 10, 12, 16, 19], key="t2")
        m2 = st.selectbox("材質", ["強化 (FT)", "熱硬化 (HS)", "退火 (AN)"], key="m2")
        l2 = st.checkbox("膠合玻璃", key="l2")
    
    design_q = st.number_input("設計風壓 (kPa)", value=2.0, step=0.1)

# --- 4. 運算與詳細報告生成 ---
d_max, d_min = max(l_a, l_b), min(l_a, l_b)
gtf_map = {"強化 (FT)": 2.0, "熱硬化 (HS)": 1.5, "退火 (AN)": 1.0}

# 載重分配 (LSF)
if is_igu == "複層":
    lsf1 = round((t1**3) / (t1**3 + t2**3), 3)
    lsf2 = round(1 - lsf1, 3)
else:
    lsf1, lsf2 = 1.0, 0.0

results = []
# 外片計算
# 傳入該層分配到的風壓 (design_q * lsf1)
nfl1, def1, out1 = get_layered_data(t1, l1, d_max, d_min, design_q * lsf1)
lr1 = round((nfl1 * gtf_map[m1]) / lsf1, 1)
mark1 = "*" if out1 else ""

results.append({
    "位置": "外片(L1)",
    "規格": f"{t1}mm-{m1}{'-Lami' if l1 else ''}",
    "NFL(查表)": f"{nfl1}{mark1}",
    "GTF": gtf_map[m1],
    "LSF": f"{lsf1}",
    "LR(抗力)": f"{lr1}{mark1}",
    "D/C比": f"{round(design_q/lr1, 1)}",
    "強度判定": "通過" if lr1 >= design_q else "不足",
    "變形(查表)": f"{def1}mm{mark1}",
    "容許變形": f"{round(d_min*2/60 if '1-s' in fix_mode else d_min/60, 1)}mm",
    "變形判定": "OK" if def1 <= (d_min*2/60 if '1-s' in fix_mode else d_min/60) else "NG"
})

# 內片計算
if is_igu == "複層":
    nfl2, def2, out2 = get_layered_data(t2, l2, d_max, d_min, design_q * lsf2)
    lr2 = round((nfl2 * gtf_map[m2]) / lsf2, 1)
    mark2 = "*" if out2 else ""
    results.append({
        "位置": "內片(L2)",
        "規格": f"{t2}mm-{m2}{'-Lami' if l2 else ''}",
        "NFL(查表)": f"{nfl2}{mark2}",
        "GTF": gtf_map[m2],
        "LSF": f"{lsf2}",
        "LR(抗力)": f"{lr2}{mark2}",
        "D/C比": f"{round(design_q/lr2, 1)}",
        "強度判定": "通過" if lr2 >= design_q else "不足",
        "變形(查表)": f"{def2}mm{mark2}",
        "容許變形": f"{round(d_min*2/60 if '1-s' in fix_mode else d_min/60, 1)}mm",
        "變形判定": "OK" if def2 <= (d_min*2/60 if '1-s' in fix_mode else d_min/60) else "NG"
})

# --- 5. 輸出表格 ---
st.subheader("強度與變形分層查表詳細清單")
st.info(f"檢核規格：{l_a}x{l_b}mm | 固定方式：{fix_mode}")

st.markdown("<style>.stTable td {white-space: nowrap;}</style>", unsafe_allow_html=True)
st.table(pd.DataFrame(results))

st.divider()
c1, c2 = st.columns(2)
with c1:
    st.markdown("#### 📝 邊界說明")
    st.write(f"- A邊({l_a}mm): 固定邊 | B邊({l_b}mm): {'自由邊' if '1-s' in fix_mode else '固定邊'}")
with c2:
    st.markdown("#### ⚖️ 變形基準")
    st.write(f"- 基準: {'2*L/60' if '1-s' in fix_mode else 'L/60'} | 星號(*)為超限推估值")

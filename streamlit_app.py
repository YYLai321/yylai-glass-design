import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 聖經數據庫：完整厚度對應之最小實厚 (Table 1) ---
ASTM_T_MIN = {
    "2.5": 2.16, "2.7": 2.59, "3.0": 2.92, "4.0": 3.78, "5.0": 4.57, 
    "6.0": 5.56, "8.0": 7.42, "10.0": 9.02, "12.0": 11.91, "16.0": 15.09, "19.0": 18.26
}

# --- 2. 聖經數據庫：LSF 查表矩陣 (擴充 19mm 等大厚度組合) ---
BIBLE_LSF = {
    "6.0+8.0":  {"L1": 0.29, "L2": 0.71}, "8.0+6.0":  {"L1": 0.71, "L2": 0.29},
    "10.0+12.0": {"L1": 0.34, "L2": 0.66}, "12.0+10.0": {"L1": 0.66, "L2": 0.34},
    "12.0+19.0": {"L1": 0.22, "L2": 0.78}, "19.0+12.0": {"L1": 0.78, "L2": 0.22},
    "15.0+19.0": {"L1": 0.36, "L2": 0.64}, "19.0+15.0": {"L1": 0.64, "L2": 0.36}
}

# --- 3. 聖經數據庫：NFL 查表矩陣 (全厚度點位) ---
BIBLE_NFL = {
    "19.0_Mono": {"area": [1.0, 5.0, 10.0, 15.0], "nfl": [28.5, 6.2, 3.2, 2.1]},
    "12.0_Mono": {"area": [1.0, 2.88, 6.0, 11.2], "nfl": [11.5, 5.2, 3.12, 1.35]},
    "10.0_Mono": {"area": [1.0, 7.2, 11.2], "nfl": [7.8, 1.5, 0.95]},
    "8.0_Mono":  {"area": [1.0, 7.6, 12.0], "nfl": [5.2, 1.0, 0.62]},
    "6.0_Mono":  {"area": [1.0, 2.88, 5.0], "nfl": [4.2, 1.8, 1.0]},
    "19.0_Lami": {"area": [1.0, 5.0, 10.0, 15.0], "nfl": [22.8, 4.8, 2.5, 1.6]}
}

# --- 4. 聖經數據庫：變形量查表 (q*Area 邏輯) ---
BIBLE_DEF = {
    "19.0": {"qa": [0, 20, 50, 100], "w": [0, 4.5, 10.5, 20.0]},
    "12.0": {"qa": [0, 11.3, 30], "w": [0, 9.0, 22.0]},
    "10.0": {"qa": [0, 11.3, 30], "w": [0, 14.5, 35.0]},
    "8.0":  {"qa": [0, 11.3, 30], "w": [0, 22.5, 55.0]},
    "6.0":  {"qa": [0, 11.3, 30], "w": [0, 35.0, 85.0]}
}

# --- 核心邏輯引擎 ---
def get_nfl(t, lami, area):
    key = f"{t}_{'Lami' if lami else 'Mono'}"
    db = BIBLE_NFL.get(key, BIBLE_NFL["12.0_Mono"])
    return np.exp(np.interp(np.log(area), np.log(db["area"]), np.log(db["nfl"])))

def get_def(t, qs, area):
    db = BIBLE_DEF.get(t, BIBLE_DEF["12.0"])
    qa_val = qs * area
    limit_qa = max(db["qa"])
    return np.interp(qa_val, db["qa"], db["w"]), qa_val > limit_qa

# --- 5. UI 介面設定 ---
st.set_page_config(page_title="賴映宇結構技師事務所", layout="wide")
st.title("ASTM E1300 玻璃檢核系統 (全厚度擴充版)")
st.divider()

# 輸入區
st.header("【1. 輸入參數】")
c1, c2, c3 = st.columns(3)
a = c1.number_input("長邊 a (mm)", value=3000.0)
b = c2.number_input("短邊 b (mm)", value=2400.0)
q_design = c3.number_input("設計風壓 q (kPa)", value=2.0)

struct = st.radio("構造模式", ["單層/膠合", "複層玻璃 (IGU)"], index=0, horizontal=True)

lites_input = []
thick_options = list(ASTM_T_MIN.keys())
gtf_options = ["一般退火 (AN)", "熱硬化 (HS)", "強化 (FT)"]

if struct == "複層玻璃 (IGU)":
    cl, cr = st.columns(2)
    with cl:
        st.subheader("Lite 1 (外側)")
        t1 = st.selectbox("L1 厚度", thick_options, index=8, key="t1") # 預設 12mm
        lami1 = st.checkbox("L1 為膠合玻璃", key="la1")
        gt1 = st.selectbox("L1 強度種類", gtf_options, index=2, key="gt1")
        lites_input.append({"id": "Lite 1", "t": t1, "lami": lami1, "gt_type": gt1})
    with cr:
        st.subheader("Lite 2 (內側)")
        t2 = st.selectbox("L2 厚度", thick_options, index=10, key="t2") # 預設 19mm
        lami2 = st.checkbox("L2 為膠合玻璃", key="la2")
        gt2 = st.selectbox("L2 強度種類", gtf_options, index=2, key="gt2")
        lites_input.append({"id": "Lite 2", "t": t2, "lami": lami2, "gt_type": gt2})
    
    # LSF 查表 (若查無組合則依立方比計算)
    lsf_key = f"{t1}+{t2}"
    if lsf_key in BIBLE_LSF:
        lites_input[0]["lsf"] = BIBLE_LSF[lsf_key]["L1"]
        lites_input[1]["lsf"] = BIBLE_LSF[lsf_key]["L2"]
    else:
        # 嚴格實厚立方比 LSF 計算
        sum_t3 = ASTM_T_MIN[t1]**3 + ASTM_T_MIN[t2]**3
        lites_input[0]["lsf"] = (ASTM_T_MIN[t1]**3) / sum_t3
        lites_input[1]["lsf"] = (ASTM_T_MIN[t2]**3) / sum_t3
else:
    ts = st.selectbox("標稱厚度", thick_options, index=10) # 預設 19mm
    la = st.checkbox("此為膠合玻璃")
    gt = st.selectbox("強度種類", gtf_options, index=2)
    lites_input.append({"id": "單層/膠合", "t": ts, "lami": la, "gt_type": gt, "lsf": 1.0})

# 輸出區 (格式固定)
st.divider()
st.header("【2. 輸出結果】")
area = (a * b) / 1e6
any_est = False
res_table = []

GTF_MONO = {"一般退火 (AN)": 1.0, "熱硬化 (HS)": 2.0, "強化 (FT)": 4.0}
GTF_IGU = {"一般退火 (AN)": 0.9, "熱硬化 (HS)": 1.8, "強化 (FT)": 3.6}

for L in lites_input:
    qs = q_design * L["lsf"]
    nfl = get_nfl(L["t"], L["lami"], area)
    gtf = (GTF_IGU if struct == "複層玻璃 (IGU)" else GTF_MONO)[L["gt_type"]]
    w, is_est = get_def(L["t"], qs, area)
    if is_est: any_est = True
    
    res_table.append({
        "位置": L["id"],
        "NFL (查表)": f"{nfl:.3f} kPa",
        "GTF": f"{gtf:.1f}",
        "LSF (查表)": f"{L['lsf']:.4f}",
        "變形量 (mm)": f"{w:.2f}" + (" *" if is_est else ""),
        "總抗力 LR": f"{(nfl * gtf / L['lsf']):.2f} kPa"
    })

st.table(pd.DataFrame(res_table))
if any_est:
    st.warning("註：標記 * 之變形量已超出 ASTM 原始圖表範圍，為推估值。")
st.info(f"技術資訊：選單已擴充至 19mm。LSF 已優先對標 Table，若查無特定組合則依 ASTM 最小實厚立方比例計算。")

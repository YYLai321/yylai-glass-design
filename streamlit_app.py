import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 最小實厚定義 (ASTM E1300 Table 1) ---
ASTM_T = {"6.0": 5.56, "8.0": 7.42, "10.0": 9.02, "12.0": 11.91, "15.0": 15.09, "19.0": 18.26}
GTF = {"一般退火 (AN)": 1.0, "熱硬化": 1.8, "強化": 3.6}

# --- 2. 聖經數據：2-s NFL (Figure 4 數位化) ---
# 鎖定：10mm@1500=0.75, 19mm@2250=1.50
DATA_NFL_2S = {
    "10.0": {"span": [1000, 1250, 1500, 1750, 2000, 2500, 3000], "nfl": [1.68, 1.05, 0.75, 0.55, 0.42, 0.27, 0.18]},
    "19.0": {"span": [1000, 1500, 2000, 2250, 2500, 2750, 3000], "nfl": [7.55, 3.38, 1.90, 1.50, 1.22, 1.00, 0.85]},
    "8.0":  {"span": [1000, 1500, 2000, 2500, 3000], "nfl": [1.13, 0.51, 0.28, 0.18, 0.12]},
    "12.0": {"span": [1000, 1500, 2000, 2500, 3000], "nfl": [2.95, 1.32, 0.74, 0.47, 0.33]}
}

# --- 3. 聖經數據：2-s 變形量 (Figure X1.1 數位化) ---
DATA_DEF_2S = {
    "10.0": {"q": [0.5, 1.0, 2.0, 3.0, 4.2, 5.0], "w_ref": [12.8, 26.5, 52.0, 78.5, 110.2, 132.5]},
    "8.0":  {"q": [0.5, 1.0, 2.0, 3.0, 4.2, 5.0], "w_ref": [21.5, 44.2, 88.5, 132.0, 185.0, 220.0]},
    "19.0": {"q": [0.5, 1.0, 2.0, 3.0, 4.2, 5.0], "w_ref": [1.5, 3.2, 6.5, 9.8, 13.5, 16.2]}
}

def bible_lookup_2s(t_nom, span_mm, q_share):
    # NFL 查表
    db_n = DATA_NFL_2S.get(t_nom)
    nfl = np.exp(np.interp(np.log(span_mm), np.log(db_n["span"]), np.log(db_n["nfl"])))
    # 變形查表 (以 2000mm 為基準並修正)
    db_w = DATA_DEF_2S.get(t_nom)
    w_base = np.interp(q_share, db_w["q"], db_w["w_ref"])
    w_final = w_base * (span_mm / 2000)**3.8 
    return nfl, w_final

# --- 4. UI 介面 ---
st.set_page_config(page_title="賴映宇結構技師事務所", layout="wide")
st.title("玻璃強度檢核系統 (ASTM E1300-16)")
st.subheader("賴映宇結構技師事務所")
st.divider()

# A. 設計參數
st.header("1. 設計參數設定")
c1, c2, c3 = st.columns(3)
a_in = c1.number_input("長邊 a (mm)", value=5360.0)
b_in = c2.number_input("短邊 b (mm)", value=2000.0)
q_design = c3.number_input("設計風壓 q_design (kPa)", value=4.2)

# B. 配置設定
st.header("2. 玻璃配置與邊界條件")
c_type, c_cond = st.columns(2)
mode = c_type.radio("類型", ["複層玻璃 (IGU)", "單層玻璃"], horizontal=True)
b_cond = c_cond.selectbox("邊界條件", ["兩邊固定 (2-s)", "四邊固定 (4-s)"])

lites = []
if mode == "複層玻璃 (IGU)":
    cl, cr = st.columns(2)
    t1 = cl.selectbox("外側 Lite 1 (t1)", list(ASTM_T.keys()), index=2) # 10mm
    gt1 = cl.selectbox("材質 1", list(GTF.keys()), index=2) # 強化
    t2 = cr.selectbox("內側 Lite 2 (t2)", list(ASTM_T.keys()), index=1) # 8mm
    gt2 = cr.selectbox("材質 2", list(GTF.keys()), index=2) # 強化
    
    t1m, t2m = ASTM_T[t1], ASTM_T[t2]
    lsf1 = (t1m**3)/(t1m**3 + t2m**3) # 負載分配係數
    lites.append({"label": "Lite 1 (外)", "t_nom": t1, "lsf": lsf1, "gt": GTF[gt1]})
    lites.append({"label": "Lite 2 (內)", "t_nom": t2, "lsf": 1-lsf1, "gt": GTF[gt2]})
else:
    ts = st.selectbox("單層厚度", list(ASTM_T.keys()), index=2)
    gs = st.selectbox("材質", list(GTF.keys()), index=2)
    lites.append({"label": "單層玻璃", "t_nom": ts, "lsf": 1.0, "gt": GTF[gs]})

# --- 5. 計算報表 ---
st.divider()
st.subheader("📋 檢核結果報表 (依據技師指定公式)")

span = b_in if b_cond == "兩邊固定 (2-s)" else min(a_in, b_in)
l60_limit = span / 60.0
results_table = []
all_w = []

for L in lites:
    qs = q_design * L["lsf"] # 單片分擔的壓力
    nfl, w = bible_lookup_2s(L["t_nom"], span, qs)
    
    # 技師指定公式：LR = NFL * GTF / LSF
    lr_system = (nfl * L["gt"]) / L["lsf"]
    
    results_table.append({
        "檢核位置": L["label"],
        "負載分配 (LSF)": f"{L['lsf']:.4f}",
        "分擔壓力 (qs)": f"{qs:.3f} kPa",
        "NFL (查表)": f"{nfl:.3f} kPa",
        "總抗力 (NFL*GTF/LSF)": f"{lr_system:.2f} kPa",
        "強度判定": "✅ PASS" if lr_system >= q_design else "❌ FAIL",
        "變形量 (mm)": f"{w:.2f}"
    })
    all_w.append(w)

st.table(pd.DataFrame(results_table))

# 變形控制
max_w = max(all_w)
st.subheader("📋 變形量控制複核")
col_w1, col_w2 = st.columns(2)
col_w1.metric("計算最大變形量", f"{max_w:.2f} mm")
col_w2.metric("規範限值 (L/60)", f"{l60_limit:.2f} mm")

if max_w > l60_limit:
    st.error(f"❌ 變形檢核不合格 (超出 {max_w - l60_limit:.2f} mm)")
else:
    st.success("✅ 變形檢核合格")

st.info(f"技術筆記：總抗力已根據 LSF 進行還原，反映整組 IGU 的結構能力。目前跨距 L = {span} mm。")

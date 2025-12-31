import streamlit as st
import pandas as pd
import numpy as np
import io
from PIL import Image, ImageDraw

# ASTM E1300-16 最小厚度 (mm)
ASTM_T = {
    "2.5 (3/32\")": 2.16, "3.0 (1/8\")": 2.92, "4.0 (5/32\")": 3.78, 
    "5.0 (3/16\")": 4.57, "6.0 (1/4\")": 5.56, "8.0 (5/16\")": 7.42, 
    "10.0 (3/8\")": 9.02, "12.0 (1/2\")": 11.91, "16.0 (5/8\")": 15.09, 
    "19.0 (3/4\")": 18.26
}

GTF_S = {"一般退火 (AN)": 1.0, "半強化 (HS)": 2.0, "全強化 (FT)": 4.0}
GTF_I = {"一般退火 (AN)": 1.0, "半強化 (HS)": 1.8, "全強化 (FT)": 3.6}

# --- 核心：ASTM E1300-16 Appendix X1 變形量公式解 ---
def get_astm_w(q_kpa, a_mm, b_mm, t_mm):
    """
    嚴格執行 SI 單位換算：Pa, m
    Target: 1920x1520x8mm @ 4.22kPa -> ~23.5mm
    """
    if q_kpa <= 0 or t_mm <= 0: return 0.0
    
    # 1. 單位強制轉換 (SI)
    q_pa = q_kpa * 1000.0   # kPa to Pa
    a_m = a_mm / 1000.0     # mm to m
    b_m = b_mm / 1000.0     # mm to m
    t_m = t_mm / 1000.0     # mm to m
    E = 71.7e9              # 71.7 GPa to Pa
    
    # 2. 長寬比 AR 與 無因次載重 q_hat
    AR = max(a_m/b_m, b_m/a_m)
    if AR > 5.0: AR = 5.0
    
    # 公式: q_hat = (q * Area^2) / (E * t^4)
    q_hat = (q_pa * (a_m * b_m)**2) / (E * (t_m**4))
    
    # 3. Table X1.1 係數
    r0 = 0.553 - 3.83 * AR + 1.11 * (AR**2) - 0.0969 * (AR**3)
    r1 = -2.29 + 5.83 * AR - 2.17 * (AR**2) + 0.2067 * (AR**3)
    r2 = 1.485 - 1.908 * AR + 0.815 * (AR**2) - 0.0822 * (AR**3)
    
    # 4. 無因次變形 w_hat
    ln_q = np.log(q_hat)
    ln_w = r0 + r1 * ln_q + r2 * (ln_q**2)
    w_hat = np.exp(ln_w)
    
    # 5. 回推實際變形 w (mm) = w_hat * t_min (mm)
    return w_hat * t_mm

def get_nfl(a, b, t):
    area = (a * b) / 1e6
    ar = max(a/b, b/a)
    # 1520x1920 @ 6mm=1.80, 8mm=2.40 基準擬合
    base = 0.1189 * (t**2.08) / (area**0.925)
    ar_factor = 1.0 / (0.92 + 0.14 * (ar - 1.0)**0.75)
    return base * ar_factor

# --- Streamlit UI ---
st.title("🛡️ 玻璃檢核系統 (ASTM E1300-16)")
st.markdown("#### **賴映宇結構技師事務所**")

# 輸入區
with st.container():
    c1, c2, c3 = st.columns(3)
    a_in = c1.number_input("長邊 a (mm)", value=1920.0)
    b_in = c2.number_input("短邊 b (mm)", value=1520.0)
    q_in = c3.number_input("設計風壓 q (kPa)", value=6.0)

mode = st.radio("模式", ["單層 (Single)", "複層 (IG Unit)"], horizontal=True)
current_gtf = GTF_I if mode == "複層 (IG Unit)" else GTF_S

configs = []
if mode == "單層 (Single)":
    t_sel = st.selectbox("厚度", list(ASTM_T.keys()), index=5)
    gt_sel = st.selectbox("材質", list(current_gtf.keys()))
    configs.append({"t": t_sel, "gtf": current_gtf[gt_sel], "label": "單層"})
else:
    cl1, cl2 = st.columns(2)
    with cl1:
        t1 = st.selectbox("Lite 1 (外側 6mm)", list(ASTM_T.keys()), index=4)
        gt1 = st.selectbox("Lite 1 材質", list(current_gtf.keys()), index=2)
        configs.append({"t": t1, "gtf": current_gtf[gt1], "label": "Lite 1 (外)"})
    with cl2:
        t2 = st.selectbox("Lite 2 (內側 8mm)", list(ASTM_T.keys()), index=5)
        gt2 = st.selectbox("Lite 2 材質", list(current_gtf.keys()), index=0)
        configs.append({"t": t2, "gtf": current_gtf[gt2], "label": "Lite 2 (內)"})

# --- 計算 ---
t_mins = [ASTM_T[c["t"]] for c in configs]
sum_t3 = sum([tm**3 for tm in t_mins])
l60 = min(a_in, b_in) / 60.0

final_data = []
for i, tm in enumerate(t_mins):
    lsf = (tm**3) / sum_t3
    actual_q = q_in * lsf
    
    # 變形量精確計算
    w = get_astm_w(actual_q, a_in, b_in, tm)
    
    # 強度計算
    nfl = get_nfl(a_in, b_in, tm)
    lr = (nfl * configs[i]["gtf"]) / lsf
    
    final_data.append({
        "位置": configs[i]["label"],
        "分擔壓力 (kPa)": round(actual_q, 2),
        "抗力 LR (kPa)": round(lr, 2),
        "強度判定": "✅ PASS" if lr >= q_in else "❌ FAIL",
        "變形量 (mm)": round(w, 2),
        "限值 L/60": round(l60, 2),
        "變形判定": "✅ 通過" if w <= l60 else "❌ 請增加厚度"
    })

st.divider()
st.subheader("📊 檢核結果摘要")
st.table(pd.DataFrame(final_data))

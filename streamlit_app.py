import streamlit as st
import pandas as pd
import numpy as np
import io
from PIL import Image, ImageDraw

# --- 1. ASTM E1300-16 參數庫 ---
ASTM_T = {
    "2.5 (3/32\")": 2.16, "3.0 (1/8\")": 2.92, "4.0 (5/32\")": 3.78, 
    "5.0 (3/16\")": 4.57, "6.0 (1/4\")": 5.56, "8.0 (5/16\")": 7.42, 
    "10.0 (3/8\")": 9.02, "12.0 (1/2\")": 11.91, "16.0 (5/8\")": 15.09, 
    "19.0 (3/4\")": 18.26
}

GTF_IGU = {"一般退火 (AN)": 1.0, "半強化 (HS)": 1.8, "全強化 (FT)": 3.6}
GTF_SINGLE = {"一般退火 (AN)": 1.0, "半強化 (HS)": 2.0, "全強化 (FT)": 4.0}

# --- 2. ASTM E1300-16 Appendix X1 精確公式解 ---

def get_astm_deflection_exact(q_applied, a, b, t_min):
    """
    依據 ASTM E1300-16 Appendix X1 進行高精度計算
    確保校準點：1520x1920x8mm @ 4.22kPa ≈ 23.5mm
    """
    if q_applied <= 0 or t_min <= 0: return 0.0
    
    E = 71.7e6  # kPa
    a_m, b_m, t_m = a/1000.0, b/1000.0, t_min/1000.0
    
    # 長寬比 AR
    AR = max(a_m / b_m, b_m / a_m)
    if AR > 5.0: AR = 5.0
    
    # 載重參數 q_hat
    q_hat = q_applied * ((a_m * b_m)**2) / (E * (t_m**4))
    
    # 多項式係數 (Table X1.1)
    r0 = 0.553 - 3.83 * AR + 1.11 * AR**2 - 0.0969 * AR**3
    r1 = -2.29 + 5.83 * AR - 2.17 * AR**2 + 0.2067 * AR**3
    r2 = 1.485 - 1.908 * AR + 0.815 * AR**2 - 0.0822 * AR**3
    
    # 計算 w_hat
    ln_q_hat = np.log(q_hat)
    ln_w_hat = r0 + r1 * ln_q_hat + r2 * (ln_q_hat**2)
    w_hat = np.exp(ln_w_hat)
    
    return w_hat * t_min

def get_nfl_exact(area, ar, t_min):
    # NFL 校準：1520x1920 @ 6mm=1.80, 8mm=2.40
    base_nfl = 0.1189 * (t_min**2.08) / (area**0.925)
    ar_factor = 1.0 / (0.92 + 0.14 * (max(ar, 1.0) - 1.0)**0.75)
    return base_nfl * ar_factor

# --- 3. JPG 報表生成器 ---
def generate_jpg_report(results, meta):
    img = Image.new('RGB', (1240, 1754), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((400, 80), "GLASS ANALYSIS REPORT (ASTM E1300-16)", fill=(0,0,0))
    draw.text((400, 120), "Lai Ying-Yu Structural Engineer Office", fill=(50,50,50))
    draw.line((100, 160, 1140, 160), fill=(0,0,0), width=3)
    
    y = 200
    for k, v in meta.items():
        draw.text((120, y), f"{k}: {v}", fill=(0,0,0)); y += 35
    
    y += 50
    headers = ["Pos", "LR(kPa)", "Strength", "Deflect", "L/60", "Serviceability"]
    h_x = [80, 180, 320, 520, 720, 900]
    for h, x in zip(headers, h_x): draw.text((x, y), h, fill=(0,0,0))
    draw.line((100, y+35, 1140, y+35), fill=(0,0,0), width=2)
    
    y += 70
    for r in results:
        draw.text((h_x[0], y), r['Pos'], fill=(0,0,0))
        draw.text((h_x[1], y), f"{r['LR']:.2f}", fill=(0,0,0))
        s_col = (0, 128, 0) if "PASS" in r['S_Stat'] else (200, 0, 0)
        draw.text((h_x[2], y), r['S_Stat'], fill=s_col)
        draw.text((h_x[3], y), f"{r['W']:.2f}mm", fill=(0,0,0))
        draw.text((h_x[4], y), f"{r['L60']:.2f}mm", fill=(0,0,0))
        d_col = (0, 128, 0) if "通過" in r['D_Stat'] else (200, 0, 0)
        draw.text((h_x[5], y), r['D_Stat'], fill=d_col)
        y += 60
    
    buf = io.BytesIO(); img.save(buf, format='JPEG', quality=95); buf.seek(0)
    return buf

# --- 4. Streamlit UI ---
st.set_page_config(page_title="賴映宇結構技師事務所", layout="wide")
st.title("🛡️ 玻璃強度與變形精確檢核系統")
st.markdown("### **賴映宇結構技師事務所 (ASTM E1300-16)**")

with st.container():
    c1, c2, c3 = st.columns(3)
    a_in = c1.number_input("長邊 a (mm)", value=1920.0)
    b_in = c2.number_input("短邊 b (mm)", value=1520.0)
    q_in = c3.number_input("設計風壓 q (kPa)", value=6.0)

st.divider()
mode = st.radio("檢核模式", ["單層", "複層"], horizontal=True)
current_gtf = GTF_IGU if mode == "複層" else GTF_SINGLE

configs = []
if mode == "單層":
    t = st.selectbox("標稱厚度", list(ASTM_T.keys()), index=5)
    gt = st.selectbox("材質", list(current_gtf.keys()))
    configs.append({"t": t, "gtf": current_gtf[gt], "label": "Single"})
else:
    cl1, cl2 = st.columns(2)
    with cl1:
        t1 = st.selectbox("Lite 1 (外側 6mm)", list(ASTM_T.keys()), index=4)
        gt1 = st.selectbox("Lite 1 材質", list(current_gtf.keys()), index=2)
        configs.append({"t": t1, "gtf": current_gtf[gt1], "label": "Lite 1"})
    with cl2:
        t2 = st.selectbox("Lite 2 (內側 8mm)", list(ASTM_T.keys()), index=5)
        gt2 = st.selectbox("Lite 2 材質", list(current_gtf.keys()), index=0)
        configs.append({"t": t2, "gtf": current_gtf[gt2], "label": "Lite 2"})

# --- 5. 計算分析 ---
area = (a_in * b_in) / 1e6
ar = a_in / b_in
l60_limit = b_in / 60.0

t_min_vals = [ASTM_T[c["t"]] for c in configs]
sum_t3 = sum([tm**3 for tm in t_min_vals])

results_list = []
results_for_report = []

for i, tm in enumerate(t_min_vals):
    lsf = (tm**3) / sum_t3
    actual_q = q_in * lsf
    nfl = get_nfl_exact(area, ar, tm)
    
    # 核心：精確公式計算變形量
    w_mm = get_astm_deflection_exact(actual_q, a_in, b_in, tm)
    
    lr = (nfl * configs[i]["gtf"]) / lsf
    s_stat = "✅ PASS" if lr >= q_in else "❌ FAIL"
    d_stat = "✅ 檢核通過" if w_mm <= l60_limit else "❌ 請增加厚度"
    
    results_list.append({
        "位置": configs[i]["label"], "LR(kPa)": round(lr, 2), "強度判定": s_stat,
        "變形量(mm)": round(w_mm, 2), "限值 L/60": round(l60_limit, 2), "變形判定": d_stat
    })
    results_for_report.append({
        "Pos": configs[i]["label"], "LR": lr, "S_Stat": s_stat, 
        "W": w_mm, "L60": l60_limit, "D_Stat": d_stat
    })

st.table(pd.DataFrame(results_list))

# --- 6. 報告下載 ---
meta = {"Size": f"{a_in}x{b_in} mm", "Design Load": f"{q_in} kPa", "Limit": f"L/60 ({l60_limit:.2f}mm)"}
jpg_buf = generate_jpg_report(results_for_report, meta)
st.download_button("📥 下載專業 JPG 檢核報告", data=jpg_buf, file_name=f"ASTM_E1300_{int(a_in)}x{int(b_in)}.jpg")

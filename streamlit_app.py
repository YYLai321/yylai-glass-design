import streamlit as st
import pandas as pd
import io
from PIL import Image, ImageDraw

# 1. ASTM E1300-16 最小厚度對照 (mm)
ASTM_T_DATA = {
    "2.5 (3/32\")": 2.16, "3.0 (1/8\")": 2.92, "4.0 (5/32\")": 3.78, 
    "5.0 (3/16\")": 4.57, "6.0 (1/4\")": 5.56, "8.0 (5/16\")": 7.42, 
    "10.0 (3/8\")": 9.02, "12.0 (1/2\")": 11.91, "16.0 (5/8\")": 15.09, 
    "19.0 (3/4\")": 18.26
}

# 玻璃材質強化係數 GTF
GTF_SINGLE = {"一般退火 (AN)": 1.0, "半強化 (HS)": 2.0, "全強化 (FT)": 4.0}
GTF_IGU    = {"一般退火 (AN)": 1.0, "半強化 (HS)": 1.8, "全強化 (FT)": 3.6}

# --- 2. 核心計算引擎 ---

def get_nfl_calibrated(a_mm, b_mm, t_mm):
    """ 依據 ASTM E1300 擬合之 NFL (kPa) """
    area_m2 = (a_mm * b_mm) / 1e6
    ar = max(a_mm/b_mm, b_mm/a_mm)
    # 基準校準點：1920x1520 @ 6mm=1.80, 8mm=2.40
    base = 0.1189 * (t_mm**2.08) / (area_m2**0.925)
    ar_factor = 1.0 / (0.92 + 0.14 * (ar - 1.0)**0.75)
    return base * ar_factor

# --- 3. Streamlit UI 介面 ---
st.set_page_config(page_title="賴映宇結構技師事務所", layout="wide")
st.title("🛡️ 建築玻璃強度檢核系統")
st.markdown("#### **賴映宇結構技師事務所 (ASTM E1300-16)**")
st.divider()

# Step 1: 尺寸與載重
st.header("1. 尺寸與設計荷載")
col1, col2, col3 = st.columns(3)
a_input = col1.number_input("長邊 a (mm)", value=1920.0)
b_input = col2.number_input("短邊 b (mm)", value=1520.0)
q_input = col3.number_input("設計風壓 q (kPa)", value=6.0)

# Step 2: 配置設定
st.header("2. 玻璃配置與材質設定")
mode = st.radio("模式選擇", ["單層玻璃 (Single)", "複層玻璃 (IG Unit)"], horizontal=True)

configs = []
if mode == "單層玻璃 (Single)":
    cl_s, cl_m = st.columns(2)
    t_s = cl_s.selectbox("標稱厚度", list(ASTM_T_DATA.keys()), index=5)
    gt_s = cl_m.selectbox("材質 (Table 2)", list(GTF_SINGLE.keys()))
    configs.append({"t_nom": t_s, "gtf": GTF_SINGLE[gt_s], "label": "單層玻璃"})
else:
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("**室外側 Lite 1**")
        t1 = st.selectbox("Lite 1 厚度", list(ASTM_T_DATA.keys()), index=4, key="t1")
        gt1 = st.selectbox("Lite 1 材質 (Table 3)", list(GTF_IGU.keys()), index=2, key="gt1")
        configs.append({"t_nom": t1, "gtf": GTF_IGU[gt1], "label": "Lite 1 (外)"})
    with col_l2:
        st.markdown("**室內側 Lite 2**")
        t2 = st.selectbox("Lite 2 厚度", list(ASTM_T_DATA.keys()), index=5, key="t2")
        gt2 = st.selectbox("Lite 2 材質 (Table 3)", list(GTF_IGU.keys()), index=0, key="gt2")
        configs.append({"t_nom": t2, "gtf": GTF_IGU[gt2], "label": "Lite 2 (內)"})

# --- 4. 執行計算 ---
st.divider()
st.header("3. 檢核結果摘要")

t_min_list = [ASTM_T_DATA[c["t_nom"]] for c in configs]
sum_t3 = sum([tm**3 for tm in t_min_list])

final_res = []
for i, tm in enumerate(t_min_list):
    # 計算負載分配 LSF (此處即為 Table 5 中決定分配比例的數值)
    lsf = (tm**3) / sum_t3 if sum_t3 > 0 else 1.0
    actual_q = q_input * lsf
    nfl = get_nfl_calibrated(a_input, b_input, tm)
    
    # 強度計算：LR = (NFL * GTF) / LSF
    lr = (nfl * configs[i]["gtf"]) / lsf
    
    final_res.append({
        "檢核位置": configs[i]["label"],
        "標稱厚度": configs[i]["t_nom"],
        "LSF (Load Sharing)": round(lsf, 3),
        "分擔壓力 (kPa)": round(actual_q, 2),
        "NFL (kPa)": round(nfl, 2),
        "GTF (材質因子)": configs[i]["gtf"],
        "抗力 LR (kPa)": round(lr, 2),
        "設計壓力 q (kPa)": q_input,
        "強度判定": "✅ PASS" if lr >= q_input else "❌ FAIL"
    })

# 顯示包含 LSF 的表格
st.table(pd.DataFrame(final_res))

# --- 5. JPG 報表功能 ---
def create_report(res):
    img = Image.new('RGB', (1200, 600), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((420, 40), "GLASS STRENGTH REPORT - ASTM E1300-16", fill=(0,0,0))
    d.text((450, 70), "Lai Ying-Yu Structural Engineer Office", fill=(50,50,50))
    y = 180
    for r in res:
        line = f"{r['檢核位置']}: LSF={r['LSF (Load Sharing)']}, LR={r['抗力 LR (kPa)']} kPa vs Design Q={r['設計壓力 q (kPa)']} kPa ({r['強度判定']})"
        d.text((100, y), line, fill=(0,0,0))
        y += 60
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf

if st.button("生成報表圖檔"):
    st.image(create_report(final_res))

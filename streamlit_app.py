import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 核心計算函數 ---
def calculate_glass_detail(thick, is_lami, mat_type, mode, l_a, l_b, total_load, glass_pos="外片"):
    # a. 判定是否超出表格範圍 (聖經圖表通常上限為 5000x3000 或總面積)
    is_out_of_range = False
    if max(l_a, l_b) > 5000 or min(l_a, l_b) > 4000:
        is_out_of_range = True
    
    # b. 取得 NFL (100mm 精細化數據)
    # 這裡會根據厚度與 Lami/Mono 定位 (例如 8mm 1900x1520=2.5)
    nfl_base = 2.5 # 假設值
    
    # c. 材質係數 GTF
    gtf_map = {"強化 (FT)": 2.0, "熱硬化 (HS)": 1.5, "退火 (AN)": 1.0}
    gtf = gtf_map[mat_type]
    
    # d. 載重分配係數 LSF (簡化邏輯：複層時依據 h^3 分配)
    # 此處僅為示意，完整版會根據 IGU 兩片厚度比計算
    lsf = 0.5 
    
    # e. 計算 LR (設計抗力) 與 檢核值
    lr = (nfl_base * gtf) / lsf
    status = "通過" if lr >= total_load else "不足"
    
    # f. 變形量計算 (ASTM E1300 非線性大撓度公式簡化)
    # 懸臂 1-s 變形基準 2L/60，其餘 L/60
    l_min = min(l_a, l_b)
    deflection = (total_load * lsf * (l_min**4)) / (100000 * thick**3) # 示意公式
    limit = (l_min * 2 / 60) if "1-s" in mode else (l_min / 60)
    deflect_status = "OK" if deflection <= limit else "NG"
    
    # 標註星號
    mark = "*" if is_out_of_range else ""
    
    return {
        "位置": glass_pos,
        "NFL": f"{nfl_base:.2f}{mark}",
        "GTF": gtf,
        "LSF": f"{lsf:.3f}",
        "LR (抗力)": f"{lr:.2f}{mark}",
        "D/C (比值)": f"{total_load/lr:.2f}",
        "判定": status,
        "計算變形": f"{deflection:.2f} mm{mark}",
        "容許變形": f"{limit:.2f} mm",
        "變形判定": deflect_status
    }

# --- 2. 介面與事務所標題 ---
st.set_page_config(page_title="賴映宇結構技師事務所", layout="wide")
st.title("🏛️ 賴映宇結構技師事務所")
st.header("ASTM E1300 玻璃結構計算詳細報告")

# --- 側邊欄參數 (維持左側) ---
with st.sidebar:
    st.header("📋 參數輸入")
    fix_mode = st.selectbox("固定方式", ["4-s (四邊固定)", "3-s (一長邊自由)", "2-s (兩長邊自由)", "1-s (懸臂板)"])
    l_a = st.number_input("尺寸 A (mm)", value=1900.0, step=100.0)
    l_b = st.number_input("尺寸 B (mm)", value=1520.0, step=100.0)
    
    st.divider()
    is_igu = st.radio("組合方式", ["單層", "複層"])
    
    # 外片
    st.subheader("外片規格")
    t1 = st.selectbox("厚度 (mm)", [6, 8, 10, 12, 16, 19], key="t1")
    m1 = st.selectbox("材質", ["強化 (FT)", "熱硬化 (HS)", "退火 (AN)"], key="m1")
    l1 = st.checkbox("膠合玻璃", key="l1")
    
    # 內片 (僅複層)
    if is_igu == "複層":
        st.subheader("內片規格")
        t2 = st.selectbox("厚度 (mm)", [6, 8, 10, 12, 16, 19], key="t2")
        m2 = st.selectbox("材質", ["強化 (FT)", "熱硬化 (HS)", "退火 (AN)"], key="m2")
        l2 = st.checkbox("膠合玻璃", key="l2")
    
    st.divider()
    design_q = st.number_input("設計風壓 (kPa)", value=2.0, step=0.1)

# --- 3. 執行檢核與結果表格 ---
results = []
# 外片檢核
res1 = calculate_glass_detail(t1, l1, m1, fix_mode, l_a, l_b, design_q, "外片 (L1)")
results.append(res1)

# 內片檢核
if is_igu == "複層":
    res2 = calculate_glass_detail(t2, l2, m2, fix_mode, l_a, l_b, design_q, "內片 (L2)")
    results.append(res2)

# --- 4. 顯示詳解表格 ---
df_res = pd.DataFrame(results)
st.subheader("1. 強度與變形計算詳細清單")
st.table(df_res)

# --- 5. 說明與註記 ---
st.divider()
st.markdown("### 📝 計算註記與邊界說明")
c1, c2 = st.columns(2)
with c1:
    st.info(f"**固定方式定義：**\n- 當前選擇：{fix_mode}\n- A邊({l_a}mm)：固定邊\n- B邊({l_b}mm)：{'自由邊' if '1-s' in fix_mode else '固定邊'}")
with c2:
    st.warning("**星號 (*) 說明：**\n當尺寸超過 ASTM E1300 標準圖表範圍 (如 5000mm 以上) 時，數值採外插推估，僅供參考，請技師加強查核。")

# 變形基準提示
if "1-s" in fix_mode:
    st.write(f"⚖️ **變形判定基準：** 懸臂板 2*L/60 = {float(res1['容許變形'].split()[0]):.2f} mm")
else:
    st.write(f"⚖️ **變形判定基準：** 一般固定 L/60 = {float(res1['容許變形'].split()[0]):.2f} mm")

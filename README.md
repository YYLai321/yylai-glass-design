import streamlit as st
import pandas as pd

# 1. 設置標題與側邊欄 (輸入長寬)
st.title("ASTM E1300 玻璃強度檢核報告")
width = st.number_input("輸入短邊 b (mm)", value=1000)
length = st.number_input("輸入長邊 a (mm)", value=2000)

# 2. 顯示計算與查表依據 (Table 4, Fig A1.x)
st.subheader("📊 檢核明細與 ASTM 溯源")

# 假設計算後的輸出表格
check_data = {
    "項目": ["最小厚度 (t_min)", "NFL 基準荷載", "種類係數 (GTF)"],
    "計算值": ["5.56 mm", "1.25 kPa", "4.0"],
    "ASTM E1300 參考位置": ["Table 4", "Fig. A1.5", "Table 1"] # 這裡會標註具體是哪張圖
}
st.table(pd.DataFrame(check_data))

# 3. 判定結果
st.success("✅ 通過檢核 (符合 ASTM E1300 標準)")

import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

st.set_page_config(page_title="PDF 解鎖工具", page_icon="🔓")

st.title("🔓 PDF 解鎖工具")
st.write("上傳一個被密碼保護的 PDF，輸入密碼後解鎖並下載。")

uploaded_file = st.file_uploader("上傳 PDF 檔案", type=["pdf"])
password = st.text_input("輸入 PDF 密碼", type="password")

if uploaded_file and password:
    try:
        reader = PdfReader(uploaded_file)

        if reader.is_encrypted:
            reader.decrypt(password)

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        # 輸出成 BytesIO
        output_stream = BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)

        st.success("✅ PDF 已成功解鎖！")
        st.download_button(
            label="下載解鎖後的 PDF",
            data=output_stream,
            file_name="unlocked.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"❌ 解鎖失敗，請確認密碼是否正確。錯誤訊息: {e}")

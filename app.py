import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO


st.set_page_config(page_title="PDF 工具箱", page_icon="📂")

st.title("📂 PDF 工具箱")
st.write("選擇功能並操作 PDF，所有處理都在本地端完成，確保安全性。")

# Sidebar 功能選擇
option = st.sidebar.radio(
    "選擇功能",
    ("🔓 PDF 解鎖", "🔒 PDF 上鎖", "📎 PDF 合併", "✂️ PDF 擷取 / 重新排序")
)

# =========================
# 1. PDF 解鎖
# =========================
if option == "🔓 PDF 解鎖":
    uploaded_file = st.file_uploader("上傳被密碼保護的 PDF", type=["pdf"])
    password = st.text_input("輸入 PDF 密碼", type="password")

    if uploaded_file and password:
        try:
            reader = PdfReader(uploaded_file)

            if reader.is_encrypted:
                result = reader.decrypt(password)
                if result == 0:
                    st.error("❌ 密碼錯誤，請重新輸入。")
                    st.stop()

            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)

            output_stream = BytesIO()
            writer.write(output_stream)
            output_stream.seek(0)

            st.success("✅ PDF 已成功解鎖！")
            if st.download_button(
                label="下載解鎖後的 PDF",
                data=output_stream,
                file_name="unlocked.pdf",
                mime="application/pdf"
            ):
                output_stream.close()
                del output_stream
                st.info("💡 暫存檔案已刪除。")

        except Exception as e:
            st.error(f"❌ 解鎖失敗，錯誤訊息: {e}")

# =========================
# 1.5. PDF 上鎖 (新增功能)
# =========================
elif option == "🔒 PDF 上鎖":
    st.header("🔒 PDF 上鎖")
    uploaded_file = st.file_uploader("上傳您要加密的 PDF", type=["pdf"])
    
    # 設置密碼
    password = st.text_input("輸入您要設定的密碼", type="password")
    confirm_password = st.text_input("確認密碼", type="password")

    if uploaded_file and password and confirm_password:
        if password != confirm_password:
            st.error("❌ 兩次輸入的密碼不一致，請重新輸入。")
            st.stop()
            
        if st.button("開始加密"):
            try:
                reader = PdfReader(uploaded_file)

                # 檢查原始檔案是否已經加密
                if reader.is_encrypted:
                    st.warning("⚠️ 檔案本身可能已加密。我們將使用新密碼重新加密。")
                    # 這裡可以選擇讓使用者先解鎖，但為了簡化，我們直接讀取頁面。
                    # 如果使用者沒有輸入原始密碼，這段可能會失敗。
                    # 為了確保功能正常，我們預設要求上傳未加密或使用者知道密碼的檔案。
                
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)

                # 使用設定的密碼進行加密 (encrypt)
                writer.encrypt(password)

                output_stream = BytesIO()
                writer.write(output_stream)
                output_stream.seek(0)

                st.success("✅ PDF 已成功上鎖！")
                if st.download_button(
                    label="下載加密後的 PDF",
                    data=output_stream,
                    file_name="locked.pdf",
                    mime="application/pdf"
                ):
                    output_stream.close()
                    del output_stream
                    st.info("💡 暫存檔案已刪除。")

            except Exception as e:
                st.error(f"❌ 上鎖失敗，錯誤訊息: {e}")
# =========================
# 2. PDF 合併
# =========================
elif option == "📎 PDF 合併":
    uploaded_files = st.file_uploader(
        "上傳多個 PDF（依照上傳順序合併）",
        type=["pdf"],
        accept_multiple_files=True
    )

    if uploaded_files:
        writer = PdfWriter()
        try:
            for file in uploaded_files:
                reader = PdfReader(file)
                for page in reader.pages:
                    writer.add_page(page)

            output_stream = BytesIO()
            writer.write(output_stream)
            output_stream.seek(0)

            st.success("✅ PDF 已成功合併！")
            if st.download_button(
                label="下載合併後的 PDF",
                data=output_stream,
                file_name="merged.pdf",
                mime="application/pdf"
            ):
                output_stream.close()
                del output_stream
                st.info("💡 暫存檔案已刪除。")

        except Exception as e:
            st.error(f"❌ 合併失敗，錯誤訊息: {e}")

# =========================
# 3. PDF 擷取 / 重新排序
# =========================
elif option == "✂️ PDF 擷取 / 重新排序":
    uploaded_file = st.file_uploader("上傳 PDF 檔案", type=["pdf"])

    if uploaded_file:
        reader = PdfReader(uploaded_file)
        total_pages = len(reader.pages)
        st.info(f"📄 總頁數：{total_pages}")

        order_input = st.text_input(
            "輸入頁面範圍或順序 (例如: 1-5、1,3,5、3,1,2、2-4,1)"
        )

        if order_input:
            try:
                new_order = []
                parts = order_input.split(",")
                for part in parts:
                    if "-" in part:
                        start, end = map(int, part.split("-"))
                        new_order.extend(range(start, end + 1))
                    else:
                        new_order.append(int(part))

                new_order = [p for p in new_order if 1 <= p <= total_pages]

                if not new_order:
                    st.error("❌ 輸入的頁碼無效")
                    st.stop()

                writer = PdfWriter()
                for p in new_order:
                    writer.add_page(reader.pages[p - 1])

                output_stream = BytesIO()
                writer.write(output_stream)
                output_stream.seek(0)

                st.success(f"✅ 已輸出 PDF，共 {len(new_order)} 頁！")
                if st.download_button(
                    label="下載輸出後的 PDF",
                    data=output_stream,
                    file_name="processed.pdf",
                    mime="application/pdf"
                ):
                    output_stream.close()
                    del output_stream
                    st.info("💡 暫存檔案已刪除。")

            except Exception as e:
                st.error(f"❌ 處理失敗，錯誤訊息: {e}")

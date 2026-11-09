import streamlit as st
import pymupdf as fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO


# =========================
# 裁切 + 合併至 A4 的輔助函式
# =========================
A4_W, A4_H = 595.0, 842.0  # pt


def detect_content_rect(page, threshold=245, dpi=50):
    """渲染成低解析度灰階圖，找出非白色內容的外框（回傳頁面座標 pt）。"""
    pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
    w, h, samples = pix.width, pix.height, pix.samples
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        row = samples[y * w:(y + 1) * w]
        if min(row) >= threshold:
            continue
        first = next(i for i, v in enumerate(row) if v < threshold)
        last = w - 1 - next(i for i, v in enumerate(reversed(row)) if v < threshold)
        x0, x1 = min(x0, first), max(x1, last)
        y0 = min(y0, y)
        y1 = y
    if x1 < 0:  # 整頁空白
        return page.rect
    scale = 72 / dpi
    return fitz.Rect(x0 * scale, y0 * scale, (x1 + 1) * scale, (y1 + 1) * scale)


def crop_rect(page, auto, padding, margins):
    """回傳要裁切的區域（頁面可見座標）。margins = (左, 上, 右, 下)。"""
    if auto:
        r = detect_content_rect(page) + (-padding, -padding, padding, padding)
    else:
        l, t, rt, b = margins
        r = fitz.Rect(page.rect.x0 + l, page.rect.y0 + t, page.rect.x1 - rt, page.rect.y1 - b)
    r = r & page.rect
    return r if not r.is_empty else page.rect


def build_a4(doc_a, doc_b, layout, outer_margin, gap, auto, padding, margins):
    """A、B 逐頁配對，每一對輸出到同一張 A4。頁數不同時，較短者以空白補齊。"""
    out = fitz.open()
    inner_w, inner_h = A4_W - 2 * outer_margin, A4_H - 2 * outer_margin
    if layout == "上下":
        slot_h = (inner_h - gap) / 2
        slots = [fitz.Rect(outer_margin, outer_margin, A4_W - outer_margin, outer_margin + slot_h),
                 fitz.Rect(outer_margin, A4_H - outer_margin - slot_h, A4_W - outer_margin, A4_H - outer_margin)]
    else:
        slot_w = (inner_w - gap) / 2
        slots = [fitz.Rect(outer_margin, outer_margin, outer_margin + slot_w, A4_H - outer_margin),
                 fitz.Rect(A4_W - outer_margin - slot_w, outer_margin, A4_W - outer_margin, A4_H - outer_margin)]

    for i in range(max(len(doc_a), len(doc_b))):
        sheet = out.new_page(width=A4_W, height=A4_H)
        for doc, slot in ((doc_a, slots[0]), (doc_b, slots[1])):
            if i >= len(doc):
                continue
            page = doc[i]
            clip = crop_rect(page, auto, padding, margins)
            # clip 以「可見」座標計算，show_pdf_page 需要未旋轉座標
            sheet.show_pdf_page(slot, doc, i, clip=clip * page.derotation_matrix, rotate=-page.rotation)
    return out.tobytes(garbage=3, deflate=True)


st.set_page_config(page_title="PDF 工具箱", page_icon="📂")

st.title("📂 PDF 工具箱")
st.write("選擇功能並操作 PDF，所有處理都在本地端完成，確保安全性。")

# Sidebar 功能選擇
option = st.sidebar.radio(
    "選擇功能",
    ("🔓 PDF 解鎖", "🔒 PDF 上鎖", "📎 PDF 合併", "✂️ PDF 擷取 / 重新排序", "🖨️ 裁切並合併至 A4")
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

# =========================
# 4. 裁切並合併至 A4
# =========================
elif option == "🖨️ 裁切並合併至 A4":
    st.header("🖨️ 裁切並合併至 A4")
    st.write("將兩份 PDF 的內容區域裁切後，並排到同一張 A4（第 N 頁配第 N 頁），適合節省影印紙張。")

    col1, col2 = st.columns(2)
    file_a = col1.file_uploader("PDF A", type=["pdf"], key="a4_a")
    file_b = col2.file_uploader("PDF B", type=["pdf"], key="a4_b")

    layout = st.radio("排版方式", ("上下", "左右"), horizontal=True)
    crop_mode = st.radio("裁切方式", ("自動偵測內容範圍", "手動設定邊距"), horizontal=True)
    auto = crop_mode == "自動偵測內容範圍"
    padding, margins = 8, (0, 0, 0, 0)
    if auto:
        padding = st.slider("內容外留白 (pt)", 0, 50, 8)
    else:
        c = st.columns(4)
        margins = tuple(c[i].number_input(n, 0, 500, 0) for i, n in enumerate(("左裁切", "上裁切", "右裁切", "下裁切")))
    c1, c2 = st.columns(2)
    outer_margin = c1.slider("A4 外邊距 (pt)", 0, 60, 20)
    gap = c2.slider("兩份內容間距 (pt)", 0, 60, 20)

    if file_a and file_b:
        try:
            doc_a = fitz.open(stream=file_a.getvalue(), filetype="pdf")
            doc_b = fitz.open(stream=file_b.getvalue(), filetype="pdf")
            if doc_a.needs_pass or doc_b.needs_pass:
                st.error("❌ 檔案有密碼保護，請先使用「PDF 解鎖」。")
                st.stop()

            result = build_a4(doc_a, doc_b, layout, outer_margin, gap, auto, padding, margins)

            st.success(f"✅ 已輸出，共 {max(len(doc_a), len(doc_b))} 張 A4！")
            preview = fitz.open(stream=result, filetype="pdf")[0].get_pixmap(dpi=80).tobytes("png")
            st.image(preview, caption="第 1 張預覽", width=360)
            st.download_button(
                label="下載 A4 合併 PDF",
                data=result,
                file_name="a4_combined.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"❌ 處理失敗，錯誤訊息: {e}")

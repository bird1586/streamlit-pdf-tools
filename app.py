import streamlit as st
import pymupdf as fitz  # PyMuPDF
from PIL import Image
from streamlit_cropper import st_cropper

import a4_layout as a4
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO


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
    PREVIEW_DPI = 100
    PX2PT = 72 / PREVIEW_DPI

    @st.cache_data(show_spinner=False)
    def page_image(pdf_bytes, pno):
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return doc[pno].get_pixmap(dpi=PREVIEW_DPI).tobytes("png")

    @st.cache_data(show_spinner=False)
    def auto_rect(pdf_bytes, pno, padding):
        page = fitz.open(stream=pdf_bytes, filetype="pdf")[pno]
        r = a4.detect_content_rect(page) + (-padding, -padding, padding, padding)
        r = r & page.rect
        return tuple(r) if not r.is_empty else tuple(page.rect)

    @st.cache_data(show_spinner="排版中…")
    def do_pack(sizes, margin, gap, allow_rotate):
        items = [a4.Item(0, i, fitz.Rect(0, 0, w, h)) for i, (w, h) in enumerate(sizes)]
        a4.fit_scales(items, a4.A4_W - 2 * margin, a4.A4_H - 2 * margin)
        sheets = a4.pack(items, margin, gap, allow_rotate)
        return sheets

    st.header("🖨️ 裁切並合併至 A4")
    st.write("可上傳多份 PDF，逐頁拖曳框選要保留的內容。輸出時**維持原尺寸（不縮放）**，"
             "自動旋轉並排版，用最少張 A4 印完。")

    files = st.file_uploader("上傳一個或多個 PDF", type=["pdf"], accept_multiple_files=True, key="a4_files")
    if not files:
        st.stop()

    # ---- 讀取檔案 ----
    srcs = []  # (file_id, name, bytes, page_count)
    for f in files:
        data = f.getvalue()
        try:
            d = fitz.open(stream=data, filetype="pdf")
            if d.needs_pass:
                st.error(f"❌ 「{f.name}」有密碼保護，請先使用「PDF 解鎖」。")
                st.stop()
            srcs.append((f.file_id, f.name, data, len(d)))
        except Exception as e:
            st.error(f"❌ 無法讀取「{f.name}」：{e}")
            st.stop()

    ss = st.session_state
    ss.setdefault("a4_crops", {})   # "fid:page" -> (x0, y0, x1, y1) pt，使用者手動調整過的裁切框
    ss.setdefault("a4_skip", set())  # 不輸出的頁面
    ss.setdefault("a4_ver", 0)       # 批次操作後遞增，讓裁切元件重建
    ss.setdefault("a4_init", {})

    with st.expander("⚙️ 設定", expanded=False):
        c1, c2, c3 = st.columns(3)
        padding = c1.slider("自動偵測：內容外留白 (pt)", 0, 50, 8)
        margin = c2.slider("A4 外邊距 (pt)", 0, 60, 20)
        gap = c3.slider("區塊間距 (pt)", 0, 40, 6)
        allow_rotate = st.checkbox("允許自動旋轉 90° 以節省空間", value=True)
        draw_border = st.checkbox("畫出虛線框線（方便剪下）", value=True)

    def key_of(fi, pno):
        return f"{srcs[fi][0]}:{pno}"

    def current_rect(fi, pno):
        return ss.a4_crops.get(key_of(fi, pno)) or auto_rect(srcs[fi][2], pno, padding)

    # ---- 逐頁裁切 ----
    st.subheader("① 裁切")
    labels = [f"{name}（{n} 頁）" for _, name, _, n in srcs]
    fi = labels.index(st.selectbox("選擇 PDF", labels)) if len(srcs) > 1 else 0
    n_pages = srcs[fi][3]
    pno = (st.number_input("頁碼", 1, n_pages, 1) - 1) if n_pages > 1 else 0
    k = key_of(fi, pno)
    pdf_bytes = srcs[fi][2]

    img = Image.open(BytesIO(page_image(pdf_bytes, pno)))
    init = ss.a4_init.setdefault((k, ss.a4_ver, padding), current_rect(fi, pno))
    coords = (int(init[0] / PX2PT), int(init[2] / PX2PT), int(init[1] / PX2PT), int(init[3] / PX2PT))  # (xl, xr, yt, yb)

    st.caption("拖曳藍框移動、拉邊角調整大小；框內即為保留範圍。")
    box = st_cropper(img, realtime_update=True, default_coords=coords, box_color="#1f77ff",
                     return_type="box", key=f"crop_{k}_{ss.a4_ver}_{padding}")
    page_rect = fitz.Rect(0, 0, img.width * PX2PT, img.height * PX2PT)
    rect = fitz.Rect(box["left"] * PX2PT, box["top"] * PX2PT,
                     (box["left"] + box["width"]) * PX2PT, (box["top"] + box["height"]) * PX2PT) & page_rect
    if rect.is_empty or rect.width < 5 or rect.height < 5:
        rect = fitz.Rect(*current_rect(fi, pno))
    rect_t = tuple(round(v, 1) for v in rect)
    if rect_t != tuple(round(v, 1) for v in current_rect(fi, pno)):
        ss.a4_crops[k] = rect_t

    st.write(f"此頁裁切尺寸：**{rect.width / a4.PT_PER_MM:.0f} × {rect.height / a4.PT_PER_MM:.0f} mm**")
    include = st.checkbox("輸出此頁", value=k not in ss.a4_skip, key=f"inc_{k}_{ss.a4_ver}")
    if include:
        ss.a4_skip.discard(k)
    else:
        ss.a4_skip.add(k)

    b1, b2, b3 = st.columns(3)
    if b1.button("🔄 此頁重設為自動偵測"):
        ss.a4_crops.pop(k, None)
        ss.a4_ver += 1
        st.rerun()
    if b2.button("📋 套用此框到本 PDF 全部頁"):
        for p in range(n_pages):
            ss.a4_crops[key_of(fi, p)] = rect_t
        ss.a4_ver += 1
        st.rerun()
    if b3.button("⚡ 全部頁面重設為自動偵測"):
        ss.a4_crops.clear()
        ss.a4_ver += 1
        st.rerun()

    # ---- 排版 ----
    st.subheader("② 排版結果")
    entries = [(i, p) for i, s in enumerate(srcs) for p in range(s[3]) if key_of(i, p) not in ss.a4_skip]
    if not entries:
        st.warning("沒有要輸出的頁面。")
        st.stop()
    sizes = []
    for i, p in entries:
        r = fitz.Rect(*current_rect(i, p))
        sizes.append((round(r.width, 1), round(r.height, 1)))

    try:
        sheets = do_pack(tuple(sizes), margin, gap, allow_rotate)
    except Exception as e:
        st.error(f"❌ 排版失敗：{e}")
        st.stop()
    items_preview = [a4.Item(0, j, fitz.Rect(0, 0, w, h)) for j, (w, h) in enumerate(sizes)]
    shrunk = a4.fit_scales(items_preview, a4.A4_W - 2 * margin, a4.A4_H - 2 * margin)
    stt = a4.stats(items_preview, sheets, margin)

    m1, m2, m3 = st.columns(3)
    m1.metric("輸出頁面數", stt["items"])
    m2.metric("A4 張數", stt["sheets"], delta=f"省 {stt['items'] - stt['sheets']} 張", delta_color="normal")
    m3.metric("版面利用率", f"{stt['utilization']:.0%}")
    if shrunk:
        names = "、".join(f"{srcs[entries[j][0]][1]} 第{entries[j][1] + 1}頁" for j in shrunk)
        st.warning(f"⚠️ 以下裁切區塊比一張 A4 還大，已等比縮小至剛好放進一張：{names}")

    # ---- 輸出 ----
    docs = [fitz.open(stream=s[2], filetype="pdf") for s in srcs]
    items = []
    for (i, p), j in zip(entries, range(len(entries))):
        items.append(a4.Item(i, p, fitz.Rect(*current_rect(i, p))))
    a4.fit_scales(items, a4.A4_W - 2 * margin, a4.A4_H - 2 * margin)
    result = a4.render(docs, items, sheets, draw_border)

    prev = fitz.open(stream=result, filetype="pdf")
    cols = st.columns(min(len(prev), 3))
    for n, pg in enumerate(prev):
        cols[n % len(cols)].image(pg.get_pixmap(dpi=60).tobytes("png"), caption=f"第 {n + 1} 張")

    st.download_button("⬇️ 下載 A4 PDF", result, "a4_combined.pdf", "application/pdf", type="primary")

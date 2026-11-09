"""裁切後的 PDF 頁面 → 1:1 原尺寸、自動旋轉排版到最少張 A4。

與 Streamlit 無關的純函式，方便單獨測試。
"""
import math
from dataclasses import dataclass

import pymupdf as fitz
from rectpack import (GuillotineBssfSas, MaxRectsBaf, MaxRectsBlsf, MaxRectsBssf, PackingBin,
                      PackingMode, SkylineBlWm, newPacker)
from rectpack.packer import SORT_AREA, SORT_LSIDE, SORT_PERI

A4_W, A4_H = 595.0, 842.0  # pt (1pt = 1/72 inch)
PT_PER_MM = 72 / 25.4


@dataclass
class Item:
    """一個要被排版的裁切區塊。"""
    doc: int            # docs 串列中的索引
    page: int           # 頁碼 (0-based)
    clip: fitz.Rect     # 裁切區域，以「可見方向」的頁面座標 (pt) 表示
    scale: float = 1.0  # 1.0 = 原尺寸；僅在區塊比整張 A4 還大時才會 < 1

    @property
    def w(self):
        return self.clip.width * self.scale

    @property
    def h(self):
        return self.clip.height * self.scale


@dataclass
class Placement:
    item: int           # items 串列中的索引
    x: float            # 相對於 A4 左上角 (pt)
    y: float
    rotated: bool


def detect_content_rect(page, threshold=245, dpi=50):
    """渲染成低解析度灰階圖，找出非白色內容外框（回傳可見座標 pt）。"""
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
        return fitz.Rect(page.rect)
    s = 72 / dpi
    return fitz.Rect(x0 * s, y0 * s, (x1 + 1) * s, (y1 + 1) * s)


def fit_scales(items, avail_w, avail_h):
    """區塊若連旋轉後都放不進一張 A4 可印區，才等比縮小到剛好放得下；其餘維持 1.0。
    回傳被縮小的 item 索引清單。"""
    shrunk = []
    for i, it in enumerate(items):
        w, h = it.clip.width, it.clip.height
        fits = (w <= avail_w and h <= avail_h) or (h <= avail_w and w <= avail_h)
        if fits:
            it.scale = 1.0
            continue
        s = max(min(avail_w / w, avail_h / h), min(avail_w / h, avail_h / w)) * 0.999
        it.scale = s
        shrunk.append(i)
    return shrunk


def pack(items, margin=20.0, gap=6.0, allow_rotate=True):
    """把 items 排到最少張 A4。回傳 sheets: list[list[Placement]]。

    使用 rectpack 的 MaxRects / Skyline / Guillotine 等多種演算法與排序，
    取張數最少者（旋轉由 rectpack 自動決定）。
    """
    if not items:
        return []
    avail_w, avail_h = int(A4_W - 2 * margin), int(A4_H - 2 * margin)
    g = int(math.ceil(gap))
    # 每個區塊向右/下多留 gap，bin 也多加 gap，這樣區塊之間剛好隔 gap、邊緣不浪費。
    dims = [(math.ceil(it.w) + g, math.ceil(it.h) + g) for it in items]
    bin_w, bin_h = avail_w + g, avail_h + g

    best = None
    for algo in (MaxRectsBssf, MaxRectsBaf, MaxRectsBlsf, SkylineBlWm, GuillotineBssfSas):
        for sort in (SORT_AREA, SORT_LSIDE, SORT_PERI):
            packer = newPacker(mode=PackingMode.Offline, bin_algo=PackingBin.BBF,
                               pack_algo=algo, sort_algo=sort, rotation=allow_rotate)
            packer.add_bin(bin_w, bin_h, count=len(items))
            for i, (w, h) in enumerate(dims):
                packer.add_rect(w, h, rid=i)
            packer.pack()
            rects = packer.rect_list()
            if len(rects) != len(items):
                continue
            n = len({r[0] for r in rects})
            if best is None or n < best[0]:
                best = (n, rects)
    if best is None:
        raise ValueError("排版失敗：有區塊無法放入 A4")

    order = sorted({r[0] for r in best[1]})
    sheets = [[] for _ in order]
    for b, x, y, w, h, rid in best[1]:
        pw, ph = dims[rid]
        rotated = (w, h) == (ph, pw) and pw != ph
        sheets[order.index(b)].append(Placement(rid, margin + float(x), margin + float(y), rotated))
    for s in sheets:
        s.sort(key=lambda p: p.item)
    return sheets


def render(docs, items, sheets, draw_border=True):
    """依排版結果輸出 A4 PDF（bytes）。區塊以 1:1 貼上，不縮放。"""
    # show_pdf_page 會把 clip 與「旋轉後」的頁面範圍相交，旋轉頁會因此被誤裁。
    # 所以先把用到的來源頁旋轉暫時歸零，自行以 rotate 參數補償，結束後還原。
    saved = {}
    for it in items:
        page = docs[it.doc][it.page]
        key = (it.doc, it.page)
        if key not in saved:
            saved[key] = (page.rotation, page.derotation_matrix)
            page.set_rotation(0)
    out = fitz.open()
    try:
        for sheet in sheets:
            page_out = out.new_page(width=A4_W, height=A4_H)
            for pl in sheet:
                it = items[pl.item]
                rotation, derot = saved[(it.doc, it.page)]
                w, h = (it.h, it.w) if pl.rotated else (it.w, it.h)
                rect = fitz.Rect(pl.x, pl.y, pl.x + w, pl.y + h)
                page_out.show_pdf_page(
                    rect, docs[it.doc], it.page, clip=it.clip * derot,
                    rotate=(-rotation + (90 if pl.rotated else 0)) % 360)
                if draw_border:
                    page_out.draw_rect(rect, color=(0.6, 0.6, 0.6), width=0.3, dashes="[2 2] 0")
        return out.tobytes(garbage=3, deflate=True)
    finally:
        for (di, pi), (rotation, _) in saved.items():
            docs[di][pi].set_rotation(rotation)


def stats(items, sheets, margin):
    used = sum(it.w * it.h for it in items)
    cap = (A4_W - 2 * margin) * (A4_H - 2 * margin) * max(len(sheets), 1)
    return {"items": len(items), "sheets": len(sheets), "utilization": used / cap}

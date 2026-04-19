import io
import fitz  # PyMuPDF
from flask import Blueprint, render_template, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
from utils.file_utils import make_zip

bp = Blueprint("pdf", __name__)

try:
    RESAMPLING = Image.Resampling.BICUBIC
except AttributeError:
    RESAMPLING = Image.BICUBIC

WATERMARK_DIRECTION_ANGLES = {
    "horizontal": 0.0,
    "diagonal-asc": 45.0,
    "diagonal-desc": -45.0,
    "vertical": 90.0,
}


# ── Page Routes ──────────────────────────────────

@bp.route("/merge")
def merge_page():
    return render_template("upload_tool.html",
        title="Merge PDFs",
        description="Combine multiple PDF files into one document",
        endpoint="/pdf/merge",
        accept=".pdf",
        multiple=True,
        options=[])


@bp.route("/split")
def split_page():
    return render_template("upload_tool.html",
        title="Split PDF",
        description="Split a PDF into individual pages or custom ranges",
        endpoint="/pdf/split",
        accept=".pdf",
        multiple=False,
        options=[
            {"type": "text", "name": "pages", "label": "Page ranges (leave empty for all pages)",
             "placeholder": "e.g. 1-3, 5, 7-10"},
        ])


@bp.route("/compress")
def compress_page():
    return render_template("upload_tool.html",
        title="Compress PDF",
        description="Reduce PDF file size by compressing images and cleaning up",
        endpoint="/pdf/compress",
        accept=".pdf",
        multiple=False,
        options=[
            {"type": "select", "name": "quality", "label": "Compression Level",
             "choices": [
                 {"value": "medium", "label": "Medium (good balance)"},
                 {"value": "low", "label": "Maximum compression"},
                 {"value": "high", "label": "Minimal compression"},
             ]},
        ])


@bp.route("/rotate")
def rotate_page():
    return render_template("upload_tool.html",
        title="Rotate PDF",
        description="Rotate all or specific pages of a PDF",
        endpoint="/pdf/rotate",
        accept=".pdf",
        multiple=False,
        options=[
            {"type": "select", "name": "angle", "label": "Rotation Angle",
             "choices": [
                 {"value": "90", "label": "90° Clockwise"},
                 {"value": "180", "label": "180°"},
                 {"value": "270", "label": "90° Counter-clockwise"},
             ]},
            {"type": "text", "name": "pages", "label": "Pages to rotate (leave empty for all)",
             "placeholder": "e.g. 1, 3, 5-7"},
        ])


@bp.route("/resize")
def resize_page():
    return render_template("upload_tool.html",
        title="Resize PDF",
        description="Change the page dimensions of a PDF",
        endpoint="/pdf/resize",
        accept=".pdf",
        multiple=False,
        options=[
            {"type": "select", "name": "mode", "label": "Resize Mode",
             "choices": [
                 {"value": "scale", "label": "Scale by percentage"},
                 {"value": "paper", "label": "Standard paper size"},
             ]},
            {"type": "number", "name": "scale", "label": "Scale (%)", "default": 100, "min": 10, "max": 500,
             "depends_on": {"mode": "scale"}},
            {"type": "select", "name": "paper", "label": "Paper Size",
             "choices": [
                 {"value": "a4", "label": "A4 (210 x 297 mm)"},
                 {"value": "letter", "label": "Letter (8.5 x 11 in)"},
                 {"value": "a3", "label": "A3 (297 x 420 mm)"},
                 {"value": "a5", "label": "A5 (148 x 210 mm)"},
                 {"value": "legal", "label": "Legal (8.5 x 14 in)"},
             ],
             "depends_on": {"mode": "paper"}},
        ])


@bp.route("/page-numbers")
def page_numbers_page():
    return render_template("upload_tool.html",
        title="Add Page Numbers",
        description="Add page numbers to each page of a PDF",
        endpoint="/pdf/page-numbers",
        accept=".pdf",
        multiple=False,
        options=[
            {"type": "select", "name": "position", "label": "Position",
             "choices": [
                 {"value": "bottom-center", "label": "Bottom Center"},
                 {"value": "bottom-right", "label": "Bottom Right"},
                 {"value": "bottom-left", "label": "Bottom Left"},
                 {"value": "top-center", "label": "Top Center"},
                 {"value": "top-right", "label": "Top Right"},
                 {"value": "top-left", "label": "Top Left"},
             ]},
            {"type": "number", "name": "start", "label": "Start number", "default": 1, "min": 0},
            {"type": "number", "name": "fontsize", "label": "Font size", "default": 11, "min": 6, "max": 30},
        ])


@bp.route("/watermark")
def watermark_page():
    return render_template("upload_tool.html",
        title="Watermark PDF",
        description="Add a customizable text or image watermark across your PDF pages",
        notes=(
            "<p>Add a watermark to the whole document or only selected pages.</p>"
            "<p>Use text or upload an image, then control placement, opacity, layer, and rotation. "
            "PNG files with transparency work best for image watermarks.</p>"
        ),
        endpoint="/pdf/watermark",
        accept=".pdf",
        multiple=False,
        options=[
            {"type": "select", "name": "watermark_type", "label": "Watermark Type",
             "choices": [
                 {"value": "text", "label": "Text watermark"},
                 {"value": "image", "label": "Image watermark"},
             ]},
            {"type": "textarea", "name": "watermark_text", "label": "Watermark Text",
             "default": "CONFIDENTIAL", "rows": 3,
             "placeholder": "Enter the text to repeat across the PDF",
             "depends_on": {"watermark_type": "text"}},
            {"type": "color", "name": "text_color", "label": "Text Color",
             "default": "#9aa0a6",
             "depends_on": {"watermark_type": "text"}},
            {"type": "number", "name": "fontsize", "label": "Font Size (pt)",
             "default": 48, "min": 10, "max": 240,
             "depends_on": {"watermark_type": "text"}},
            {"type": "file", "name": "watermark_image", "label": "Watermark Image",
             "accept": ".png,.jpg,.jpeg,.webp,.bmp",
             "help": "Transparent PNG is recommended for logos and stamps.",
             "depends_on": {"watermark_type": "image"}},
            {"type": "range", "name": "image_scale", "label": "Image Width",
             "default": 25, "min": 5, "max": 100, "step": 5, "suffix": "% of page width",
             "depends_on": {"watermark_type": "image"}},
            {"type": "range", "name": "opacity", "label": "Opacity",
             "default": 28, "min": 5, "max": 100, "step": 1, "suffix": "%"},
            {"type": "select", "name": "position", "label": "Placement",
             "choices": [
                 {"value": "center", "label": "Center"},
                 {"value": "top-left", "label": "Top Left"},
                 {"value": "top-center", "label": "Top Center"},
                 {"value": "top-right", "label": "Top Right"},
                 {"value": "center-left", "label": "Center Left"},
                 {"value": "center-right", "label": "Center Right"},
                 {"value": "bottom-left", "label": "Bottom Left"},
                 {"value": "bottom-center", "label": "Bottom Center"},
                 {"value": "bottom-right", "label": "Bottom Right"},
                 {"value": "tiled", "label": "Tiled across page"},
             ]},
            {"type": "select", "name": "direction", "label": "Direction / Rotation",
             "choices": [
                 {"value": "diagonal-desc", "label": "Diagonal (-45°)"},
                 {"value": "diagonal-asc", "label": "Diagonal (45°)"},
                 {"value": "horizontal", "label": "Horizontal (0°)"},
                 {"value": "vertical", "label": "Vertical (90°)"},
                 {"value": "custom", "label": "Custom angle"},
             ]},
            {"type": "number", "name": "custom_angle", "label": "Custom Angle (degrees)",
             "default": -45, "min": -360, "max": 360, "step": 1,
             "depends_on": {"direction": "custom"}},
            {"type": "select", "name": "layer", "label": "Layer",
             "choices": [
                 {"value": "under", "label": "Behind page content"},
                 {"value": "over", "label": "On top of page content"},
             ]},
            {"type": "text", "name": "pages", "label": "Pages (leave empty for all pages)",
             "placeholder": "e.g. 1-3, 5, 8-10"},
            {"type": "number", "name": "margin_x", "label": "Horizontal Margin (pt)",
             "default": 36, "min": 0, "max": 500},
            {"type": "number", "name": "margin_y", "label": "Vertical Margin (pt)",
             "default": 36, "min": 0, "max": 500},
            {"type": "number", "name": "offset_x", "label": "Horizontal Offset (pt)",
             "default": 0, "min": -500, "max": 500},
            {"type": "number", "name": "offset_y", "label": "Vertical Offset (pt)",
             "default": 0, "min": -500, "max": 500},
            {"type": "number", "name": "gap_x", "label": "Tile Gap X (pt)",
             "default": 120, "min": 0, "max": 1000,
             "depends_on": {"position": "tiled"}},
            {"type": "number", "name": "gap_y", "label": "Tile Gap Y (pt)",
             "default": 90, "min": 0, "max": 1000,
             "depends_on": {"position": "tiled"}},
        ],
        button_text="Apply Watermark")


@bp.route("/extract-images")
def extract_images_page():
    return render_template("upload_tool.html",
        title="Extract Images",
        description="Extract all images embedded in a PDF file",
        endpoint="/pdf/extract-images",
        accept=".pdf",
        multiple=False,
        options=[])


@bp.route("/protect")
def protect_page():
    return render_template("upload_tool.html",
        title="Protect PDF",
        description="Add password protection to a PDF file",
        endpoint="/pdf/protect",
        accept=".pdf",
        multiple=False,
        options=[
            {"type": "password", "name": "user_password", "label": "User Password (to open)",
             "placeholder": "Enter password"},
            {"type": "password", "name": "owner_password", "label": "Owner Password (optional, for editing)",
             "placeholder": "Leave empty to use same password"},
        ])


@bp.route("/unlock")
def unlock_page():
    return render_template("upload_tool.html",
        title="Unlock PDF",
        description="Remove password protection from a PDF",
        endpoint="/pdf/unlock",
        accept=".pdf",
        multiple=False,
        options=[
            {"type": "password", "name": "password", "label": "PDF Password",
             "placeholder": "Enter the current password"},
        ])


# ── Processing Routes ────────────────────────────

def parse_page_ranges(spec: str, total: int) -> list[int]:
    """Parse '1-3, 5, 7-10' into a list of 0-based page indices."""
    if not spec.strip():
        return list(range(total))

    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            s = max(1, int(start.strip()))
            e = min(total, int(end.strip()))
            pages.update(range(s - 1, e))
        else:
            p = int(part.strip()) - 1
            if 0 <= p < total:
                pages.add(p)
    return sorted(pages)


PAPER_SIZES = {
    "a4": (595.28, 841.89),
    "letter": (612, 792),
    "a3": (841.89, 1190.55),
    "a5": (419.53, 595.28),
    "legal": (612, 1008),
}


def _parse_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = (value or "#9aa0a6").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        return (154, 160, 166)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (154, 160, 166)


def _load_watermark_font(size: int):
    for font_name in ("DejaVuSans.ttf", "arial.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _apply_opacity(image: Image.Image, opacity_pct: float) -> Image.Image:
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    factor = _clamp(opacity_pct, 0, 100) / 100.0
    alpha = alpha.point(lambda px: int(px * factor))
    image.putalpha(alpha)
    return image


def _image_to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _build_text_watermark_asset(text: str, fontsize: int, color_hex: str,
                                opacity: float, angle: float) -> tuple[bytes, float, float]:
    scale = 4
    font_px = max(24, int(fontsize * scale))
    font = _load_watermark_font(font_px)
    lines = text.splitlines() or [text]
    text_value = "\n".join(lines)
    spacing = max(10, font_px // 4)

    probe = Image.new("RGBA", (8, 8), (255, 255, 255, 0))
    probe_draw = ImageDraw.Draw(probe)
    bbox = probe_draw.multiline_textbbox((0, 0), text_value, font=font, spacing=spacing, align="center")
    text_w = max(1, bbox[2] - bbox[0])
    text_h = max(1, bbox[3] - bbox[1])
    pad_x = max(20, font_px // 2)
    pad_y = max(16, font_px // 3)

    base = Image.new("RGBA", (text_w + pad_x * 2, text_h + pad_y * 2), (255, 255, 255, 0))
    draw = ImageDraw.Draw(base)
    fill = _hex_to_rgb(color_hex) + (int(255 * (_clamp(opacity, 0, 100) / 100.0)),)
    draw.multiline_text((pad_x, pad_y), text_value, font=font, fill=fill, spacing=spacing, align="center")

    rotated = base.rotate(angle, expand=True, resample=RESAMPLING)
    return _image_to_png_bytes(rotated), rotated.width / scale, rotated.height / scale


def _build_image_watermark_asset(file_storage, opacity: float, angle: float) -> tuple[bytes, int, int]:
    try:
        image = Image.open(io.BytesIO(file_storage.read())).convert("RGBA")
    except Exception as exc:
        raise ValueError(f"Could not read watermark image: {exc}") from exc

    image = _apply_opacity(image, opacity)
    if angle % 360:
        image = image.rotate(angle, expand=True, resample=RESAMPLING)
    return _image_to_png_bytes(image), image.width, image.height


def _resolve_watermark_angle() -> float:
    direction = request.form.get("direction", "diagonal-desc")
    if direction == "custom":
        return _parse_float(request.form.get("custom_angle", -45), -45.0)
    return WATERMARK_DIRECTION_ANGLES.get(direction, -45.0)


def _resolve_watermark_size(page_rect: fitz.Rect, asset_w: float, asset_h: float,
                            watermark_type: str, image_scale_pct: float,
                            margin_x: float, margin_y: float) -> tuple[float, float]:
    if watermark_type == "image":
        width = page_rect.width * (_clamp(image_scale_pct, 1, 100) / 100.0)
        height = width * (asset_h / asset_w)
    else:
        width, height = asset_w, asset_h

    max_w = max(24.0, page_rect.width - (margin_x * 2))
    max_h = max(24.0, page_rect.height - (margin_y * 2))
    scale = min(max_w / width if width else 1.0, max_h / height if height else 1.0, 1.0)
    return max(12.0, width * scale), max(12.0, height * scale)


def _build_watermark_rects(page_rect: fitz.Rect, item_w: float, item_h: float, position: str,
                           margin_x: float, margin_y: float, offset_x: float, offset_y: float,
                           gap_x: float, gap_y: float) -> list[fitz.Rect]:
    x_left = page_rect.x0 + margin_x + offset_x
    x_center = page_rect.x0 + ((page_rect.width - item_w) / 2.0) + offset_x
    x_right = page_rect.x1 - item_w - margin_x + offset_x
    y_top = page_rect.y0 + margin_y + offset_y
    y_center = page_rect.y0 + ((page_rect.height - item_h) / 2.0) + offset_y
    y_bottom = page_rect.y1 - item_h - margin_y + offset_y

    if position != "tiled":
        anchors = {
            "top-left": (x_left, y_top),
            "top-center": (x_center, y_top),
            "top-right": (x_right, y_top),
            "center-left": (x_left, y_center),
            "center": (x_center, y_center),
            "center-right": (x_right, y_center),
            "bottom-left": (x_left, y_bottom),
            "bottom-center": (x_center, y_bottom),
            "bottom-right": (x_right, y_bottom),
        }
        x, y = anchors.get(position, anchors["center"])
        return [fitz.Rect(x, y, x + item_w, y + item_h)]

    rects = []
    step_x = max(item_w + gap_x, item_w * 0.75)
    step_y = max(item_h + gap_y, item_h * 0.75)
    start_x = page_rect.x0 + margin_x + offset_x - step_x
    start_y = page_rect.y0 + margin_y + offset_y - step_y
    limit_x = page_rect.x1 - margin_x + step_x
    limit_y = page_rect.y1 - margin_y + step_y

    row = 0
    y = start_y
    while y < limit_y:
        stagger = step_x / 2.0 if row % 2 else 0.0
        x = start_x + stagger
        while x < limit_x:
            rect = fitz.Rect(x, y, x + item_w, y + item_h)
            if rect.intersects(page_rect):
                rects.append(rect)
            x += step_x
        y += step_y
        row += 1

    return rects


@bp.route("/merge", methods=["POST"])
def merge():
    files = request.files.getlist("files")
    if len(files) < 2:
        return jsonify(error="Please upload at least 2 PDF files."), 400

    result = fitz.open()
    for f in files:
        try:
            doc = fitz.open(stream=f.read(), filetype="pdf")
            result.insert_pdf(doc)
            doc.close()
        except Exception as e:
            return jsonify(error=f"Error reading {f.filename}: {str(e)}"), 400

    output = io.BytesIO()
    result.save(output)
    result.close()
    output.seek(0)
    return send_file(output, mimetype="application/pdf",
                     as_attachment=True, download_name="merged.pdf")


@bp.route("/split", methods=["POST"])
def split():
    files = request.files.getlist("files")
    if not files or not files[0].filename:
        return jsonify(error="No file uploaded."), 400

    page_spec = request.form.get("pages", "").strip()
    doc = fitz.open(stream=files[0].read(), filetype="pdf")

    try:
        pages = parse_page_ranges(page_spec, len(doc))
    except ValueError:
        return jsonify(error="Invalid page range format."), 400

    if not pages:
        return jsonify(error="No valid pages selected."), 400

    if len(pages) == 1:
        single = fitz.open()
        single.insert_pdf(doc, from_page=pages[0], to_page=pages[0])
        output = io.BytesIO()
        single.save(output)
        single.close()
        doc.close()
        output.seek(0)
        return send_file(output, mimetype="application/pdf",
                         as_attachment=True, download_name=f"page_{pages[0]+1}.pdf")

    parts = []
    for p in pages:
        part = fitz.open()
        part.insert_pdf(doc, from_page=p, to_page=p)
        buf = io.BytesIO()
        part.save(buf)
        part.close()
        parts.append((f"page_{p + 1}.pdf", buf.getvalue()))

    doc.close()
    zip_buf = make_zip(parts)
    return send_file(zip_buf, mimetype="application/zip",
                     as_attachment=True, download_name="split_pages.zip")


@bp.route("/compress", methods=["POST"])
def compress():
    files = request.files.getlist("files")
    if not files or not files[0].filename:
        return jsonify(error="No file uploaded."), 400

    quality = request.form.get("quality", "medium")
    image_quality = {"low": 40, "medium": 65, "high": 85}.get(quality, 65)

    doc = fitz.open(stream=files[0].read(), filetype="pdf")

    for page in doc:
        images = page.get_images(full=True)
        for img_info in images:
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue
                img_bytes = base_image["image"]
                from PIL import Image
                pil_img = Image.open(io.BytesIO(img_bytes))
                if pil_img.mode in ("RGBA", "P"):
                    pil_img = pil_img.convert("RGB")
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=image_quality, optimize=True)
                doc._deleteObject(xref)
                page.insert_image(page.rect, stream=buf.getvalue())
            except Exception:
                continue

    output = io.BytesIO()
    doc.save(output, garbage=4, deflate=True, clean=True)
    doc.close()
    output.seek(0)

    name = files[0].filename.rsplit(".", 1)[0] + "_compressed.pdf"
    return send_file(output, mimetype="application/pdf",
                     as_attachment=True, download_name=name)


@bp.route("/rotate", methods=["POST"])
def rotate():
    files = request.files.getlist("files")
    if not files or not files[0].filename:
        return jsonify(error="No file uploaded."), 400

    angle = int(request.form.get("angle", 90))
    page_spec = request.form.get("pages", "").strip()

    doc = fitz.open(stream=files[0].read(), filetype="pdf")
    pages = parse_page_ranges(page_spec, len(doc))

    for p in pages:
        doc[p].set_rotation((doc[p].rotation + angle) % 360)

    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)

    name = files[0].filename.rsplit(".", 1)[0] + "_rotated.pdf"
    return send_file(output, mimetype="application/pdf",
                     as_attachment=True, download_name=name)


@bp.route("/resize", methods=["POST"])
def resize():
    files = request.files.getlist("files")
    if not files or not files[0].filename:
        return jsonify(error="No file uploaded."), 400

    mode = request.form.get("mode", "scale")
    doc = fitz.open(stream=files[0].read(), filetype="pdf")

    if mode == "scale":
        scale = float(request.form.get("scale", 100)) / 100.0
        for page in doc:
            r = page.rect
            new_rect = fitz.Rect(0, 0, r.width * scale, r.height * scale)
            page.set_mediabox(new_rect)
    elif mode == "paper":
        paper = request.form.get("paper", "a4")
        w, h = PAPER_SIZES.get(paper, PAPER_SIZES["a4"])
        for page in doc:
            page.set_mediabox(fitz.Rect(0, 0, w, h))

    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)

    name = files[0].filename.rsplit(".", 1)[0] + "_resized.pdf"
    return send_file(output, mimetype="application/pdf",
                     as_attachment=True, download_name=name)


@bp.route("/page-numbers", methods=["POST"])
def page_numbers():
    files = request.files.getlist("files")
    if not files or not files[0].filename:
        return jsonify(error="No file uploaded."), 400

    position = request.form.get("position", "bottom-center")
    start = int(request.form.get("start", 1))
    fontsize = int(request.form.get("fontsize", 11))

    doc = fitz.open(stream=files[0].read(), filetype="pdf")

    for i, page in enumerate(doc):
        num = start + i
        r = page.rect
        margin = 36  # 0.5 inch

        pos_map = {
            "bottom-center": fitz.Point(r.width / 2, r.height - margin),
            "bottom-right": fitz.Point(r.width - margin, r.height - margin),
            "bottom-left": fitz.Point(margin, r.height - margin),
            "top-center": fitz.Point(r.width / 2, margin + fontsize),
            "top-right": fitz.Point(r.width - margin, margin + fontsize),
            "top-left": fitz.Point(margin, margin + fontsize),
        }
        point = pos_map.get(position, pos_map["bottom-center"])

        align = 1 if "center" in position else (2 if "right" in position else 0)
        page.insert_text(point, str(num), fontsize=fontsize,
                         fontname="helv", color=(0.3, 0.3, 0.3))

    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)

    name = files[0].filename.rsplit(".", 1)[0] + "_numbered.pdf"
    return send_file(output, mimetype="application/pdf",
                     as_attachment=True, download_name=name)


@bp.route("/watermark", methods=["POST"])
def watermark():
    files = request.files.getlist("files")
    if not files or not files[0].filename:
        return jsonify(error="No PDF uploaded."), 400

    opacity = _clamp(_parse_float(request.form.get("opacity", 28), 28.0), 5.0, 100.0)
    position = request.form.get("position", "center")
    margin_x = max(0.0, _parse_float(request.form.get("margin_x", 36), 36.0))
    margin_y = max(0.0, _parse_float(request.form.get("margin_y", 36), 36.0))
    offset_x = _parse_float(request.form.get("offset_x", 0), 0.0)
    offset_y = _parse_float(request.form.get("offset_y", 0), 0.0)
    gap_x = max(0.0, _parse_float(request.form.get("gap_x", 120), 120.0))
    gap_y = max(0.0, _parse_float(request.form.get("gap_y", 90), 90.0))
    overlay = request.form.get("layer", "under") == "over"
    page_spec = request.form.get("pages", "").strip()
    watermark_type = request.form.get("watermark_type", "text")
    angle = _resolve_watermark_angle()

    doc = fitz.open(stream=files[0].read(), filetype="pdf")

    if doc.needs_pass:
        doc.close()
        return jsonify(error="This PDF is password protected. Unlock it first, then add a watermark."), 400

    try:
        pages = parse_page_ranges(page_spec, len(doc))
    except ValueError:
        doc.close()
        return jsonify(error="Invalid page range format."), 400

    if not pages:
        doc.close()
        return jsonify(error="No valid pages selected."), 400

    try:
        if watermark_type == "image":
            wm_file = request.files.get("watermark_image")
            if not wm_file or not wm_file.filename:
                doc.close()
                return jsonify(error="Please choose an image watermark file."), 400
            watermark_bytes, asset_w, asset_h = _build_image_watermark_asset(wm_file, opacity, angle)
            image_scale = _clamp(_parse_float(request.form.get("image_scale", 25), 25.0), 5.0, 100.0)
        else:
            text = request.form.get("watermark_text", "").strip()
            if not text:
                doc.close()
                return jsonify(error="Please enter watermark text."), 400
            fontsize = _clamp(_parse_int(request.form.get("fontsize", 48), 48), 10, 240)
            color = request.form.get("text_color", "#9aa0a6")
            watermark_bytes, asset_w, asset_h = _build_text_watermark_asset(text, fontsize, color, opacity, angle)
            image_scale = 0.0
    except ValueError as exc:
        doc.close()
        return jsonify(error=str(exc)), 400

    image_xref = 0
    for page_index in pages:
        page = doc[page_index]
        item_w, item_h = _resolve_watermark_size(page.rect, asset_w, asset_h,
                                                 watermark_type, image_scale, margin_x, margin_y)
        rects = _build_watermark_rects(page.rect, item_w, item_h, position,
                                       margin_x, margin_y, offset_x, offset_y, gap_x, gap_y)
        for rect in rects:
            image_xref = page.insert_image(rect, stream=watermark_bytes,
                                           xref=image_xref, overlay=overlay,
                                           keep_proportion=True)

    output = io.BytesIO()
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    output.seek(0)

    name = files[0].filename.rsplit(".", 1)[0] + "_watermarked.pdf"
    return send_file(output, mimetype="application/pdf",
                     as_attachment=True, download_name=name)


@bp.route("/extract-images", methods=["POST"])
def extract_images():
    files = request.files.getlist("files")
    if not files or not files[0].filename:
        return jsonify(error="No file uploaded."), 400

    doc = fitz.open(stream=files[0].read(), filetype="pdf")
    images = []

    for i, page in enumerate(doc):
        for img_idx, img_info in enumerate(page.get_images(full=True)):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue
                ext = base_image.get("ext", "png")
                images.append((f"page{i+1}_img{img_idx+1}.{ext}", base_image["image"]))
            except Exception:
                continue

    doc.close()

    if not images:
        return jsonify(error="No images found in the PDF."), 400

    if len(images) == 1:
        ext = images[0][0].rsplit(".", 1)[1]
        mime = f"image/{'jpeg' if ext in ('jpg','jpeg') else ext}"
        return send_file(io.BytesIO(images[0][1]), mimetype=mime,
                         as_attachment=True, download_name=images[0][0])

    zip_buf = make_zip(images)
    name = files[0].filename.rsplit(".", 1)[0] + "_images.zip"
    return send_file(zip_buf, mimetype="application/zip",
                     as_attachment=True, download_name=name)


@bp.route("/protect", methods=["POST"])
def protect():
    files = request.files.getlist("files")
    if not files or not files[0].filename:
        return jsonify(error="No file uploaded."), 400

    user_pw = request.form.get("user_password", "")
    owner_pw = request.form.get("owner_password", "") or user_pw

    if not user_pw:
        return jsonify(error="Please enter a password."), 400

    doc = fitz.open(stream=files[0].read(), filetype="pdf")
    perm = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY

    output = io.BytesIO()
    doc.save(output,
             encryption=fitz.PDF_ENCRYPT_AES_256,
             user_pw=user_pw,
             owner_pw=owner_pw,
             permissions=perm)
    doc.close()
    output.seek(0)

    name = files[0].filename.rsplit(".", 1)[0] + "_protected.pdf"
    return send_file(output, mimetype="application/pdf",
                     as_attachment=True, download_name=name)


@bp.route("/unlock", methods=["POST"])
def unlock():
    files = request.files.getlist("files")
    if not files or not files[0].filename:
        return jsonify(error="No file uploaded."), 400

    password = request.form.get("password", "")
    pdf_data = files[0].read()

    doc = fitz.open(stream=pdf_data, filetype="pdf")

    if doc.needs_pass:
        if not doc.authenticate(password):
            doc.close()
            return jsonify(error="Incorrect password."), 400

    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)

    name = files[0].filename.rsplit(".", 1)[0] + "_unlocked.pdf"
    return send_file(output, mimetype="application/pdf",
                     as_attachment=True, download_name=name)

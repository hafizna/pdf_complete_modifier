import copy
import os

from flask import jsonify, render_template


HOSTED_DISABLED_TOOLS = {
    ("convert", "ocr-pdf"): (
        "OCR PDF is disabled on Railway because it depends on the Tesseract binary, "
        "which is not bundled into the hosted build."
    ),
    ("convert", "cad-to-pdf"): (
        "CAD to PDF/Image is disabled on Railway because the hosted build does not "
        "include the CAD rendering stack or ODA File Converter."
    ),
    ("image", "remove-bg"): (
        "Remove Background is disabled on Railway because it needs the heavier rembg "
        "and ONNX runtime stack."
    ),
    ("image", "ocr"): (
        "Image OCR is disabled on Railway because it depends on the Tesseract binary."
    ),
    ("qr", "read"): (
        "Read QR is disabled on Railway because it depends on the ZBar shared library."
    ),
}


def is_hosted_runtime():
    return any(
        os.environ.get(name)
        for name in (
            "RAILWAY_ENVIRONMENT",
            "RAILWAY_PROJECT_ID",
            "RAILWAY_SERVICE_ID",
            "RAILWAY_PUBLIC_DOMAIN",
        )
    )


def is_tool_enabled(category_id, tool_id, hosted=None):
    if hosted is None:
        hosted = is_hosted_runtime()
    return not hosted or (category_id, tool_id) not in HOSTED_DISABLED_TOOLS


def get_visible_tool_categories(tool_categories, hosted=None):
    if hosted is None:
        hosted = is_hosted_runtime()

    filtered_categories = []
    for category in tool_categories:
        tools = [
            tool
            for tool in category["tools"]
            if is_tool_enabled(category["id"], tool["id"], hosted=hosted)
        ]
        if tools:
            category_copy = copy.deepcopy(category)
            category_copy["tools"] = tools
            filtered_categories.append(category_copy)
    return filtered_categories


def get_runtime_label(hosted=None):
    if hosted is None:
        hosted = is_hosted_runtime()
    return "Hosted on Railway" if hosted else "Runs locally"


def get_runtime_support_copy(hosted=None):
    if hosted is None:
        hosted = is_hosted_runtime()
    if hosted:
        return "Shared version tuned for the tools that run reliably in a hosted browser workflow."
    return "Private version with the full local toolset, including system-dependent extras."


def render_hosted_unavailable_tool(title, description, category_id, tool_id):
    reason = HOSTED_DISABLED_TOOLS[(category_id, tool_id)]
    notes = (
        "<p><strong>This tool is only available in the local install.</strong></p>"
        f"<p>{reason}</p>"
        "<p>The Railway version keeps the tools that work cleanly without extra system packages. "
        "If you need this one, run the app locally on your own machine.</p>"
    )
    return render_template(
        "upload_tool.html",
        title=title,
        description=description,
        notes=notes,
        endpoint="#",
        accept="",
        multiple=False,
        options=[],
        tool_disabled=True,
    )


def hosted_tool_error(category_id, tool_id):
    reason = HOSTED_DISABLED_TOOLS[(category_id, tool_id)]
    return jsonify(error=f"{reason} Use the local install for this tool."), 503

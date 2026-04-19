# Sejda At Home

A personal Flask toolkit with 29 practical tools for PDF work, image edits, and a few everyday calculators.

## Included Tools

### Document Conversion
- Files to PDF
- PDF to Word
- PDF to Images
- PDF to Text
- HTML to PDF
- OCR PDF
- CAD to PDF/Image

### PDF Tools
- Merge PDFs
- Split PDF
- Compress PDF
- Rotate PDF
- Resize PDF
- Page Numbers
- Watermark PDF
- Extract Images
- Protect PDF
- Unlock PDF

### Image Tools
- Resize Image
- Compress Image
- Convert Format
- Remove Background
- Crop Image
- Rotate / Flip
- Add Watermark
- Image to Text (OCR)

### Calculators
- Calculator
- Date Calculator
- Time Difference
- Pomodoro Timer

## Quick Start

### Requirements

- Python 3.10+

### Install

```bash
git clone https://github.com/hafizna/pdf_complete_modifier
cd pdf_complete_modifier

python -m venv venv
source venv/bin/activate
# Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Run

```bash
python app.py
```

Open `http://localhost:5000`.

### Windows Launcher

```bat
run_local.bat
```

## Optional Dependencies

Some tools need extra packages or system binaries:

| Package | Feature | Notes |
|---|---|---|
| `rembg` | Remove Background | Installs ONNX Runtime and is much heavier than the core app. |
| `pytesseract` | OCR PDF, Image to Text | Requires the Tesseract binary installed on your system. |
| `ezdxf` + `matplotlib` | CAD to PDF/Image | Required for DXF rendering. |
| ODA File Converter | DWG support | Needed if you want to open `.dwg` instead of `.dxf`. |

Install optional extras only when needed:

```bash
pip install -r requirements-optional.txt
```

## Railway

This repo includes:

- `railway.json`
- a `/health` endpoint
- `gunicorn` in the default requirements

Hosted Railway mode keeps the tools that work cleanly without extra system setup. The hosted version hides:

- `OCR PDF`
- `CAD to PDF/Image`
- `Remove Background`
- `Image to Text (OCR)`

## Project Structure

```text
pdf_complete_modifier/
|-- app.py
|-- requirements.txt
|-- requirements-optional.txt
|-- railway.json
|-- run_local.bat
|-- routes/
|   |-- convert_tools.py
|   |-- pdf_tools.py
|   |-- image_tools.py
|   `-- calculator_tools.py
|-- templates/
|   |-- base.html
|   |-- index.html
|   |-- upload_tool.html
|   `-- tools/
|       |-- calculator.html
|       |-- date_calc.html
|       |-- time_difference.html
|       `-- pomodoro.html
|-- static/
|   |-- css/style.css
|   `-- js/main.js
`-- utils/
    |-- file_utils.py
    `-- runtime.py
```

## Notes

- `upload_tool.html` is the shared template for the file-based tools.
- Calculators run fully in the browser with vanilla JavaScript.
- Most file processing stays in memory with `BytesIO`.
- The interface is custom CSS, not a CSS framework.

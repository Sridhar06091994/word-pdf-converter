import os
import shutil
import subprocess
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from pdf2docx import Converter

app = FastAPI(title="Word & PDF Converter")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit for public safety


def find_libreoffice() -> str | None:
    for cmd in ("libreoffice", "soffice"):
        found = shutil.which(cmd)
        if found:
            return found
    win_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for p in win_paths:
        if os.path.exists(p):
            return p
    return None


def remove_file(path: str):
    if os.path.exists(path):
        os.remove(path)


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/convert/word-to-pdf")
async def word_to_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".doc", ".docx")):
        raise HTTPException(status_code=400, detail="Please upload a .doc or .docx file.")

    soffice = find_libreoffice()
    if not soffice:
        raise HTTPException(
            status_code=500,
            detail="LibreOffice is not installed on this machine. Install LibreOffice for Word-to-PDF.",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.docx")
        with open(input_path, "wb") as f:
            f.write(content)

        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", input_path, "--outdir", tmpdir],
                check=True,
                timeout=45,
            )
        except Exception:
            raise HTTPException(status_code=500, detail="Word to PDF conversion failed.")

        output_pdf = os.path.join(tmpdir, "input.pdf")
        if not os.path.exists(output_pdf):
            raise HTTPException(status_code=500, detail="PDF output was not generated.")

        fd, final_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        os.replace(output_pdf, final_path)

        base_name = os.path.splitext(file.filename)[0]
        background_tasks.add_task(remove_file, final_path)

        return FileResponse(
            final_path,
            media_type="application/pdf",
            filename=f"{base_name}.pdf",
        )


@app.post("/convert/pdf-to-word")
async def pdf_to_word(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a .pdf file.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_pdf = os.path.join(tmpdir, "input.pdf")
        with open(input_pdf, "wb") as f:
            f.write(content)

        fd, final_docx = tempfile.mkstemp(suffix=".docx")
        os.close(fd)

        try:
            cv = Converter(input_pdf)
            cv.convert(final_docx)
            cv.close()
        except Exception:
            remove_file(final_docx)
            raise HTTPException(status_code=500, detail="PDF to Word conversion failed.")

        base_name = os.path.splitext(file.filename)[0]
        background_tasks.add_task(remove_file, final_docx)

        return FileResponse(
            final_docx,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{base_name}.docx",
        )
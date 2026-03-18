import os
import subprocess
from pathlib import Path

pdf_dir = Path("datasets/intern/pdfs")
output_base = Path("datasets/intern/text/2_preprocessed")

for pdf_file in pdf_dir.glob("*.pdf"):
    pdf_name = pdf_file.stem  # Name ohne .pdf
    output_dir = output_base / pdf_name
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python",
        "edc/preprocessing/pdf_to_text_and_tables.py",
        str(pdf_file),
        "--output_dir",
        str(output_dir)
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

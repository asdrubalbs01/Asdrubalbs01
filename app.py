import os
import subprocess
import uuid
from pathlib import Path

from flask import Flask, render_template, request, send_file, url_for, redirect, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-key")

BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "output"
ALLOWED_EXTENSIONS = {"pdf"}

# Ensure required directories exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def build_conversion_command(pdf_path: Path, output_folder: Path) -> list[str]:
    """
    Build the shell command used to convert the PDF into MusicXML.

    Audiveris is used by default, but the command can be swapped for any compatible
    open-source OMR tool. The command is intentionally explicit (no shell=True) for
    safety.
    """

    return [
        "audiveris",
        "-batch",
        "-export",
        "-output",
        str(output_folder),
        str(pdf_path),
    ]


def find_musicxml_file(base_name: str, search_dir: Path) -> Path | None:
    """Look for a generated MusicXML (or compressed .mxl) file in the output folder."""
    candidates = list(search_dir.glob(f"{base_name}*.musicxml"))
    if candidates:
        return candidates[0]
    candidates = list(search_dir.glob(f"{base_name}*.mxl"))
    if candidates:
        return candidates[0]
    candidates = list(search_dir.glob(f"{base_name}*.xml"))
    if candidates:
        return candidates[0]
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    if "file" not in request.files:
        flash("Aucun fichier reçu. Merci de sélectionner un PDF.", "danger")
        return redirect(url_for("index"))

    uploaded_file = request.files["file"]

    if uploaded_file.filename == "":
        flash("Le fichier sélectionné est vide. Merci de choisir un PDF valide.", "danger")
        return redirect(url_for("index"))

    if not allowed_file(uploaded_file.filename):
        flash("Seuls les fichiers PDF sont acceptés.", "danger")
        return redirect(url_for("index"))

    safe_name = secure_filename(uploaded_file.filename)
    unique_prefix = uuid.uuid4().hex
    pdf_name = f"{unique_prefix}_{safe_name}"
    pdf_path = UPLOAD_FOLDER / pdf_name
    uploaded_file.save(pdf_path)

    command = build_conversion_command(pdf_path, OUTPUT_FOLDER)

    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        flash(
            "L'outil de conversion (Audiveris) est introuvable. Merci de vérifier son installation.",
            "danger",
        )
        pdf_path.unlink(missing_ok=True)
        return redirect(url_for("index"))

    if result.returncode != 0:
        flash(
            "La conversion a échoué. Consultez les logs serveur pour plus de détails.",
            "danger",
        )
        pdf_path.unlink(missing_ok=True)
        return redirect(url_for("index"))

    base_name = pdf_path.stem
    musicxml_file = find_musicxml_file(base_name, OUTPUT_FOLDER)

    if not musicxml_file or not musicxml_file.exists():
        flash(
            "Aucun fichier MusicXML généré. Merci de vérifier la configuration de l'outil OMR.",
            "danger",
        )
        pdf_path.unlink(missing_ok=True)
        return redirect(url_for("index"))

    download_url = url_for("download_output", filename=musicxml_file.name)
    flash("Conversion réussie ! Cliquez sur le lien pour télécharger le fichier.", "success")
    return render_template(
        "index.html",
        download_url=download_url,
        output_filename=musicxml_file.name,
    )


@app.route("/download/<path:filename>")
def download_output(filename: str):
    file_path = OUTPUT_FOLDER / filename
    if not file_path.exists():
        flash("Fichier introuvable. Merci de relancer une conversion.", "danger")
        return redirect(url_for("index"))
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)

import os
import subprocess
import uuid
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-key")

BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "output"
ALLOWED_EXTENSIONS = {"pdf"}
MOCK_CONVERSION_ENABLED = os.environ.get("ENABLE_MOCK_CONVERSION", "false").lower() in {
    "1",
    "true",
    "yes",
}

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


def create_dummy_musicxml(base_name: str, output_folder: Path) -> Path:
    """
    Generate a minimal MusicXML file to let the workflow run even without Audiveris.

    This is useful for automated testing environments where the external dependency
    is unavailable. It produces a tiny MusicXML score with a single measure.
    """

    dummy_path = output_folder / f"{base_name}.musicxml"
    dummy_content = f"""
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work>
    <work-title>Dummy conversion for {base_name}</work-title>
  </work>
  <part-list>
    <score-part id="P1">
      <part-name>Music</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>whole</type>
      </note>
    </measure>
  </part>
</score-partwise>
"""
    dummy_path.write_text(dummy_content.strip(), encoding="utf-8")
    return dummy_path


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
    return render_template("index.html", mock_mode=MOCK_CONVERSION_ENABLED)


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
    base_name = pdf_path.stem

    # If mock mode is enabled, skip the external dependency and provide a tiny MusicXML file
    if MOCK_CONVERSION_ENABLED:
        musicxml_file = create_dummy_musicxml(base_name, OUTPUT_FOLDER)
        download_url = url_for("download_output", filename=musicxml_file.name)
        flash(
            "Conversion simulée (mode démo). Désactivez ENABLE_MOCK_CONVERSION pour utiliser Audiveris.",
            "warning",
        )
        return render_template(
            "index.html",
            download_url=download_url,
            output_filename=musicxml_file.name,
            mock_mode=MOCK_CONVERSION_ENABLED,
        )

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
            "L'outil de conversion (Audiveris) est introuvable. Merci de vérifier son installation ou activez ENABLE_MOCK_CONVERSION=1 pour tester sans dépendance.",
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
        mock_mode=MOCK_CONVERSION_ENABLED,
    )


@app.route("/download/<path:filename>")
def download_output(filename: str):
    file_path = OUTPUT_FOLDER / filename
    if not file_path.exists():
        flash("Fichier introuvable. Merci de relancer une conversion.", "danger")
        return redirect(url_for("index"))
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "true").lower() in {"1", "true", "yes"},
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )

from flask import Flask, request, render_template, send_file
import os
import yt_dlp
from basic_pitch.inference import predict_and_save

app = Flask(__name__)
UPLOAD_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    midi_ready = False
    if request.method == 'POST':
        url = request.form.get('youtube_url', '')
        if url:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(UPLOAD_FOLDER, 'audio.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192',
                }],
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            predict_and_save(
                [os.path.join(UPLOAD_FOLDER, 'audio.wav')],
                output_directory=UPLOAD_FOLDER,
                save_midi=True
            )
            midi_ready = True
    return render_template('index.html', midi_ready=midi_ready)

@app.route('/download')
def download():
    midi_path = os.path.join(UPLOAD_FOLDER, 'audio_basic_pitch.mid')
    return send_file(midi_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

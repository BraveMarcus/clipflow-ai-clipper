import os
import re
import uuid
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

APP_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = APP_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

FORMATS = {
    "vertical": (720, 1280),
    "square": (1080, 1080),
    "horizontal": (1280, 720),
}

def valid_youtube_url(url):
    return bool(re.match(
        r"^https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[A-Za-z0-9_-]{6,}",
        url.strip()
    ))

def srt_time(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def make_srt(segments, clip_start, clip_end, path):
    entries = []
    idx = 1
    for seg in segments:
        start = max(float(seg.start), clip_start)
        end = min(float(seg.end), clip_end)
        text = (seg.text or "").strip()
        if end <= start or not text:
            continue
        # Keep subtitle lines short enough to read on a phone.
        words = text.split()
        lines = []
        current = []
        for word in words:
            current.append(word)
            if len(" ".join(current)) > 38:
                lines.append(" ".join(current[:-1]))
                current = [word]
        if current:
            lines.append(" ".join(current))
        subtitle = "\n".join(lines[:2]).replace("-->", "→")
        entries.append(f"{idx}\n{srt_time(start-clip_start)} --> {srt_time(end-clip_start)}\n{subtitle}\n")
        idx += 1
    path.write_text("\n".join(entries), encoding="utf-8")

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/clip")
def clip_video():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    fmt = data.get("format", "vertical")
    captions = bool(data.get("captions", True))
    if not valid_youtube_url(url):
        return jsonify(error="Paste a valid YouTube video URL."), 400
    if fmt not in FORMATS:
        return jsonify(error="Choose a supported clip format."), 400

    job_id = uuid.uuid4().hex[:10]
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    source = job_dir / "source.mp4"
    try:
        subprocess.run(
            ["yt-dlp", "--no-playlist", "-f", "bv*[height<=720]+ba/b[height<=720]",
             "--merge-output-format", "mp4", "-o", str(source), url],
            check=True, timeout=240
        )
        if not source.exists():
            candidates = list(job_dir.glob("source.*"))
            if candidates:
                source = candidates[0]
            else:
                raise RuntimeError("Video download did not produce a file.")

        from faster_whisper import WhisperModel
        model = WhisperModel(os.getenv("WHISPER_MODEL", "base"), device="cpu", compute_type="int8")
        transcript_iter, info = model.transcribe(str(source), vad_filter=True)
        transcript = list(transcript_iter)
        if not transcript:
            raise RuntimeError("No speech was detected. Try a video with clear spoken audio.")

        chosen = []
        for seg in transcript:
            duration = float(seg.end) - float(seg.start)
            if 8 <= duration <= 35:
                chosen.append((float(seg.start), min(float(seg.end), float(seg.start) + 30)))
        if not chosen:
            for seg in transcript:
                if float(seg.end) - float(seg.start) >= 4:
                    chosen.append((float(seg.start), min(float(seg.end), float(seg.start) + 25)))
        chosen = chosen[:5]
        if not chosen:
            raise RuntimeError("Could not find suitable speech segments in this video.")

        width, height = FORMATS[fmt]
        clips = []
        for i, (start, end) in enumerate(chosen, 1):
            out = job_dir / f"clip-{i}.mp4"
            vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
            if captions:
                srt = job_dir / f"clip-{i}.srt"
                make_srt(transcript, start, end, srt)
                # Use FFmpeg subtitles filter; escape path characters for filter syntax.
                escaped = str(srt).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
                vf += f",subtitles='{escaped}':force_style='FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=50'"
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(start), "-i", str(source),
                "-t", str(max(1, end-start)), "-vf", vf,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)
            ], check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            clips.append({
                "title": f"Clip {i}",
                "start": round(start, 1),
                "end": round(end, 1),
                "format": fmt,
                "captions": captions,
                "url": f"/outputs/{job_id}/{out.name}"
            })
        return jsonify(clips=clips, note="Your clips are ready. Review captions and framing before posting.")
    except subprocess.TimeoutExpired:
        return jsonify(error="This video took too long to process on this server. Try a shorter video."), 504
    except FileNotFoundError:
        return jsonify(error="Server setup is incomplete: install FFmpeg and yt-dlp, then restart the app."), 500
    except Exception as e:
        return jsonify(error=f"Could not clip this video: {str(e)[:220]}"), 500

@app.get("/outputs/<job_id>/<filename>")
def output_file(job_id, filename):
    safe_name = secure_filename(filename)
    folder = OUTPUT_DIR / secure_filename(job_id)
    return send_from_directory(folder, safe_name, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)

# ClipFlow AI YouTube Clipper — updated starter

## New in this version
- Format selector: vertical 9:16, square 1:1, horizontal 16:9.
- Auto captions toggle, enabled by default.
- When captions are enabled, speech recognition creates subtitle timings and FFmpeg burns subtitles into each MP4.
- Redesigned settings panel and output cards.

## Run locally
Requires Python 3.11 and FFmpeg installed and available in PATH.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000.

## Publish
The app needs a Python host that supports Flask, FFmpeg, yt-dlp and enough CPU/RAM/disk for video processing. GitHub Pages alone only hosts static files and cannot run this backend. Free hosting tiers can sleep, time out, or limit processing; check the current plan terms before deploying.

1. Upload the extracted project files to a GitHub repository.
2. Deploy the repository to a Python-capable web host.
3. Install dependencies with `pip install -r requirements.txt`.
4. Install FFmpeg on the host if not included.
5. Start with `waitress-serve --host=0.0.0.0 --port=$PORT app:app`.
6. Test using a short public video you own or have permission to use.

This is a starter implementation, not an unlimited service. Video downloads may fail for private, age-restricted, region-restricted, live, or unavailable videos. Captions can contain transcription mistakes. Review every clip before posting, and respect copyright and YouTube terms.

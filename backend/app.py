import io
import time

from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError

from blip_service import blip
from content_generator import TONES, generate

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
CORS(app, resources={r"/api/*": {"origins": "*"}})

ALLOWED = {"image/jpeg", "image/png", "image/webp"}


@app.get("/api/health")
def health():
    return jsonify(status="ok", model_loaded=blip.ready, device=blip.device, tones=list(TONES))


@app.post("/api/generate")
def generate_content():
    file = request.files.get("image")
    if not file:
        return jsonify(error="No image uploaded. Send it as form field 'image'."), 400
    if file.mimetype not in ALLOWED:
        return jsonify(error="Unsupported file type. Use JPG, PNG or WebP."), 415
    try:
        image = Image.open(io.BytesIO(file.read()))
        image.thumbnail((1024, 1024))  # BLIP works at 384px; this just saves memory
    except UnidentifiedImageError:
        return jsonify(error="That file couldn't be read as an image."), 400

    started = time.time()
    analysis = blip.analyze(image)
    content = generate(
        analysis,
        tone=request.form.get("tone", "professional"),
        brand=request.form.get("brand", ""),
        category=request.form.get("category", ""),
    )
    return jsonify(analysis=analysis, content=content, seconds=round(time.time() - started, 2))


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="Image is larger than 10 MB."), 413


if __name__ == "__main__":
    blip.load()  # warm up so the first request is fast
    app.run(host="0.0.0.0", port=5000, debug=False)

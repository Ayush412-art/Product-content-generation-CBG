# Listwise: product content from a photo

Upload a product image and get a title, description, bullet points, tags, SEO text and alt text.
Image understanding is done by **BLIP** (open-source, runs on your machine, no external API).

```
React (Vite) ──/api/generate──▶ Flask ──▶ BLIP caption model  ─┐
                                      └─▶ BLIP VQA model      ─┴▶ rule-based copywriter ─▶ JSON
```

## Run it

### 1. Backend (Python 3.10+)
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                                     # http://localhost:5000
```
First start downloads ~2 GB of BLIP weights from Hugging Face (cached afterwards).

**Low-resource machines (8 GB RAM, CPU only):** already handled. The backend uses int8 quantization,
batches the VQA questions into one pass, and uses a single short caption. Expect roughly 1.5-2 GB of RAM
and ~10-25 s per image on a typical laptop CPU (the first request is slower while models load).
Close heavy apps/browser tabs while running. Set `BLIP_QUANTIZE=0` if you see odd answers.

### 2. Frontend (Node 18+)
```bash
cd frontend
npm install
npm run dev                                       # http://localhost:5173
```

## How it works
- `blip_service.py`: captions the image (plain + "a product photo of" prompt) and asks BLIP-VQA
  five questions: type, color, material, style, use.
- `content_generator.py`: turns those answers into copy using tone templates. Nothing is invented
  beyond what BLIP reported, and the UI shows BLIP's raw answers so you can verify them.
- `app.py`: `POST /api/generate` (multipart: `image`, `tone`, `brand`, `category`), `GET /api/health`.

## Tuning
- Better captions: `export BLIP_CAPTION_MODEL=Salesforce/blip-image-captioning-large`
- Add tones or wording: edit `TONES` in `content_generator.py`
- Add attributes (e.g. "what pattern is it?"): add to `QUESTIONS` in `blip_service.py`
- Want fluent, longer copy later? Feed `analysis` into an open LLM (e.g. Flan-T5 or Llama) inside `generate()`.

## Production notes
Use `gunicorn -w 1 --threads 4 app:app` (one worker, since each worker loads its own models),
and serve the built frontend (`npm run build`) from nginx with `/api` proxied to Flask.

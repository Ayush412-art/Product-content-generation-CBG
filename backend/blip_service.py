"""
BLIP wrapper (open-source, runs locally - no external API).

Models:
  * Salesforce/blip-image-captioning-base -> describes the image
  * Salesforce/blip-vqa-base              -> answers questions (type, color, material, style, use)

Tuned for low-resource machines (e.g. 8 GB RAM, CPU only):
  * int8 dynamic quantization of Linear layers (less RAM, faster on CPU)   BLIP_QUANTIZE=1 (default on CPU)
  * all 5 VQA questions answered in ONE batched forward pass
  * a single caption, fewer beams, short outputs
  * image downscaled to BLIP's native 384px before inference
Env toggles: BLIP_QUANTIZE=0 to disable, BLIP_CAPTION_MODEL=...-large for better captions (needs more RAM).
"""
import os
import threading

import torch
from PIL import Image
from transformers import (
    BlipForConditionalGeneration,
    BlipForQuestionAnswering,
    BlipProcessor,
)

CAPTION_MODEL = os.getenv("BLIP_CAPTION_MODEL", "Salesforce/blip-image-captioning-base")
VQA_MODEL = os.getenv("BLIP_VQA_MODEL", "Salesforce/blip-vqa-base")

QUESTIONS = {
    "type": "what kind of product is this?",
    "color": "what is the main color of the product?",
    "material": "what material is the product made of?",
    "style": "what is the style of the product?",
    "use": "what is this product used for?",
}


def _maybe_quantize(model, enabled: bool):
    if not enabled:
        return model
    try:
        return torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
    except Exception as exc:  # fall back to full precision rather than crash
        print(f"[BLIP] quantization skipped: {exc}")
        return model


class BlipService:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # int8 dynamic quantization only works on CPU
        self.quantize = self.device == "cpu" and os.getenv("BLIP_QUANTIZE", "1") == "1"
        self._lock = threading.Lock()
        self._ready = False
        if self.device == "cpu":
            torch.set_num_threads(max(1, (os.cpu_count() or 4)))

    def load(self):
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            print(f"[BLIP] loading on {self.device} (quantized={self.quantize}) ...")
            kw = {"low_cpu_mem_usage": True}
            self.cap_proc = BlipProcessor.from_pretrained(CAPTION_MODEL)
            cap = BlipForConditionalGeneration.from_pretrained(CAPTION_MODEL, **kw).eval()
            self.cap_model = _maybe_quantize(cap, self.quantize).to(self.device)

            self.vqa_proc = BlipProcessor.from_pretrained(VQA_MODEL)
            vqa = BlipForQuestionAnswering.from_pretrained(VQA_MODEL, **kw).eval()
            self.vqa_model = _maybe_quantize(vqa, self.quantize).to(self.device)
            self._ready = True
            print("[BLIP] ready")

    @property
    def ready(self):
        return self._ready

    @torch.inference_mode()
    def caption(self, image: Image.Image) -> dict:
        inputs = self.cap_proc(image, return_tensors="pt").to(self.device)
        ids = self.cap_model.generate(**inputs, max_new_tokens=30, num_beams=3, repetition_penalty=1.3)
        text = self.cap_proc.decode(ids[0], skip_special_tokens=True).strip()
        return {"plain": text, "product": text}

    @torch.inference_mode()
    def ask_all(self, image: Image.Image) -> dict:
        """All questions in one batched pass (much faster than 5 separate calls)."""
        keys, questions = list(QUESTIONS), list(QUESTIONS.values())
        inputs = self.vqa_proc(
            images=[image] * len(questions), text=questions, padding=True, return_tensors="pt"
        ).to(self.device)
        ids = self.vqa_model.generate(**inputs, max_new_tokens=8, num_beams=1)
        answers = self.vqa_proc.batch_decode(ids, skip_special_tokens=True)
        return {k: a.strip() for k, a in zip(keys, answers)}

    def analyze(self, image: Image.Image) -> dict:
        self.load()
        image = image.convert("RGB").resize((384, 384))
        with self._lock:  # one inference at a time keeps memory predictable
            captions = self.caption(image)
            attributes = self.ask_all(image)
        return {"captions": captions, "attributes": attributes}


blip = BlipService()

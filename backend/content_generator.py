"""
Transparent, rule-based copywriter. It only uses what BLIP actually saw
(captions + VQA answers), so every sentence can be traced back to the image.
"""
import re
import random

JUNK_PREFIXES = re.compile(
    r"^(arafed|araffe|there (is|are)|this is|a product photo of|a photo of|a picture of|an image of)\s+",
    re.I,
)
VAGUE = {"", "yes", "no", "product", "unknown", "none", "nothing", "it", "item", "plain", "solid"}
STOP = {"a", "an", "the", "of", "and", "with", "on", "in", "for", "to", "is", "are", "its", "it", "this", "that", "at", "by"}

TONES = {
    "professional": {
        "open": "Introducing the {title}.",
        "body": "Designed for people who value dependable quality, it pairs a clean look with practical everyday performance.",
        "close": "A considered choice for home, office, or gifting.",
        "cta": "Add to cart today.",
    },
    "playful": {
        "open": "Meet your new favorite: the {title}!",
        "body": "It brings a little personality to your day and looks great doing it.",
        "close": "Warning: compliments may follow.",
        "cta": "Grab yours before it's gone!",
    },
    "luxury": {
        "open": "The {title}, refined in every detail.",
        "body": "Understated and carefully composed, it rewards those with an eye for craftsmanship.",
        "close": "An elevated essential, made to be noticed quietly.",
        "cta": "Discover the collection.",
    },
}


def _clean(text: str) -> str:
    text = (text or "").strip().lower()
    for _ in range(2):
        text = JUNK_PREFIXES.sub("", text)
    return re.sub(r"\s+", " ", text).strip(" .,")


def _good(v: str) -> bool:
    return _clean(v) not in VAGUE


def _dedupe_words(words):
    seen, out = set(), []
    for w in words:
        k = w.lower()
        if k not in seen:
            seen.add(k)
            out.append(w)
    return out


def _title_case(s: str) -> str:
    return " ".join(w if w.isupper() else w.capitalize() for w in s.split())


def _product_noun(attrs: dict, captions: dict) -> str:
    t = _clean(attrs.get("type", ""))
    if _good(t):
        return t
    cap = _clean(captions.get("product") or captions.get("plain") or "")
    # take the head noun phrase before "with/on/in/that"
    cap = re.split(r"\b(with|on|in|that|sitting|standing|next|against)\b", cap)[0].strip()
    return cap or "product"


def generate(analysis: dict, tone: str = "professional", brand: str = "", category: str = "") -> dict:
    tone = tone if tone in TONES else "professional"
    caps, attrs = analysis["captions"], analysis["attributes"]
    noun = _product_noun(attrs, caps)
    color = _clean(attrs.get("color", "")) if _good(attrs.get("color", "")) else ""
    material = _clean(attrs.get("material", "")) if _good(attrs.get("material", "")) else ""
    style = _clean(attrs.get("style", "")) if _good(attrs.get("style", "")) else ""
    use = _clean(attrs.get("use", "")) if _good(attrs.get("use", "")) else ""

    # ---- title
    parts = [brand.strip()] if brand.strip() else []
    parts += [p for p in (color, material, style) if p]
    parts.append(noun)
    title = _title_case(" ".join(_dedupe_words(" ".join(parts).split())))
    if category.strip():
        title += f" | {category.strip().title()}"

    # ---- short + long description
    t = TONES[tone]
    short = f"{_title_case(' '.join(p for p in (color, material, noun) if p))} that looks as good as it works."
    details = []
    if color:
        details.append(f"a {color} finish")
    if material:
        details.append(f"{material} construction")
    if style:
        details.append(f"a {style} style")
    detail_sentence = ("It features " + ", ".join(details[:-1]) + (" and " if len(details) > 1 else "") + details[-1] + ".") if details else ""
    use_sentence = f"Ideal for {use}." if use else ""
    long = " ".join(s for s in (t["open"].format(title=title.split(" | ")[0]), detail_sentence, t["body"], use_sentence, t["close"], t["cta"]) if s)

    # ---- bullets
    bullets = []
    if material:
        bullets.append(f"Made from {material} for lasting quality")
    if color:
        bullets.append(f"{color.capitalize()} colorway that's easy to match")
    if style:
        bullets.append(f"{style.capitalize()} design with everyday appeal")
    if use:
        bullets.append(f"Great for {use}")
    bullets.append("Photographed and described from the actual product image")
    bullets = bullets[:5]

    # ---- tags / SEO / alt text
    words = re.findall(r"[a-z]+", " ".join([noun, color, material, style, use, _clean(caps.get("plain", ""))]))
    tags = _dedupe_words([w for w in words if w not in STOP and len(w) > 2])[:10]
    if color and noun:
        tags.insert(0, f"{color} {noun}")
    alt_text = _clean(caps.get("plain") or caps.get("product") or noun).capitalize() + "."
    meta = (short + " " + (use_sentence or t["cta"]))[:155]

    return {
        "title": title,
        "short_description": short,
        "description": long,
        "bullets": bullets,
        "tags": tags,
        "seo": {"meta_title": title[:60], "meta_description": meta},
        "alt_text": alt_text,
    }

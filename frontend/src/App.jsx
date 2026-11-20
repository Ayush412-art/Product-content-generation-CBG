import { useCallback, useEffect, useRef, useState } from "react";

const TONES = [
  { id: "professional", label: "Professional" },
  { id: "playful", label: "Playful" },
  { id: "luxury", label: "Luxury" },
];

function useCopy() {
  const [done, setDone] = useState("");
  const copy = useCallback(async (key, text) => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(key);
      setTimeout(() => setDone(""), 1400);
    } catch {
      /* clipboard blocked: ignore */
    }
  }, []);
  return [done, copy];
}

function Field({ id, label, text, copied, onCopy, children }) {
  return (
    <section className="field">
      <header>
        <h3>{label}</h3>
        <button className="ghost" onClick={() => onCopy(id, text)} aria-live="polite">
          {copied === id ? "Copied" : "Copy"}
        </button>
      </header>
      {children}
    </section>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [tone, setTone] = useState("professional");
  const [brand, setBrand] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [drag, setDrag] = useState(false);
  const [copied, copy] = useCopy();
  const inputRef = useRef(null);

  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  const pick = (f) => {
    if (!f) return;
    if (!/^image\/(jpeg|png|webp)$/.test(f.type)) return setError("Use a JPG, PNG or WebP image.");
    if (f.size > 10 * 1024 * 1024) return setError("Image must be under 10 MB.");
    setError("");
    setResult(null);
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const generate = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    const body = new FormData();
    body.append("image", file);
    body.append("tone", tone);
    body.append("brand", brand);
    body.append("category", category);
    try {
      const res = await fetch("/api/generate", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Something went wrong.");
      setResult(data);
    } catch (e) {
      setError(e.message === "Failed to fetch" ? "Can't reach the server. Start the Flask backend on port 5000." : e.message);
    } finally {
      setLoading(false);
    }
  };

  const c = result?.content;
  const a = result?.analysis;
  const everything = c
    ? `${c.title}\n\n${c.description}\n\n${c.bullets.map((b) => "- " + b).join("\n")}\n\nTags: ${c.tags.join(", ")}\nMeta: ${c.seo.meta_description}`
    : "";

  return (
    <div className="app">
     

      <main className="grid">
        {/* ---------- Stage ---------- */}
        <aside className="stage-col">
          <h1>Turn a product photo into a ready-to-publish listing.</h1>

          <div
            className={`stage ${drag ? "drag" : ""} ${preview ? "has" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
          >
            {preview ? (
              <>
                <img src={preview} alt="Uploaded product" />
                <button className="swap" onClick={() => inputRef.current.click()}>Change photo</button>
              </>
            ) : (
              <button className="drop" onClick={() => inputRef.current.click()}>
                <strong>Drop a product photo here</strong>
                <span>or browse. JPG, PNG or WebP.</span>
              </button>
            )}
            <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(e) => pick(e.target.files[0])} />
          </div>

          <div className="controls">
            <div className="row">
              <label>
                Brand <span className="opt">optional</span>
                <input value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="e.g. Kolkata Kraft" />
              </label>
              <label>
                Category <span className="opt">optional</span>
                <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. Home decor" />
              </label>
            </div>

            <fieldset className="tones">
              <legend>Tone of voice</legend>
              {TONES.map((t) => (
                <label key={t.id} className={tone === t.id ? "on" : ""}>
                  <input type="radio" name="tone" checked={tone === t.id} onChange={() => setTone(t.id)} />
                  {t.label}
                </label>
              ))}
            </fieldset>

            <button className="primary" disabled={!file || loading} onClick={generate}>
              {loading ? "Reading your photo…" : "Write the listing"}
            </button>
            {error && <p className="error" role="alert">{error}</p>}
          </div>
        </aside>

        {/* ---------- Result ---------- */}
        <section className="result-col" aria-live="polite">
          {!result && !loading && (
            <div className="empty">
              <h2>Your listing appears here</h2>
              <p>Upload a photo and choose a tone. You'll get a title, description, bullet points, tags and SEO text, plus what the model saw in your image.</p>
            </div>
          )}

          {loading && (
            <div className="skeletons" aria-label="Generating">
              {[70, 100, 90, 55].map((w, i) => <div key={i} className="sk" style={{ width: w + "%", height: i === 1 ? 92 : 22 }} />)}
              <p className="hint">The request loads can take a sometime.</p>
            </div>
          )}

          {c && !loading && (
            <article className="listing">
              <div className="listing-head">
                <h2>Listing</h2>
                <button className="ghost strong" onClick={() => copy("all", everything)}>{copied === "all" ? "Copied" : "Copy everything"}</button>
              </div>

              <Field id="title" label="Title" text={c.title} copied={copied} onCopy={copy}>
                <p className="title">{c.title}</p>
              </Field>

              <Field id="desc" label="Description" text={c.description} copied={copied} onCopy={copy}>
                <p className="lede">{c.short_description}</p>
                <p>{c.description}</p>
              </Field>

              <Field id="bul" label="Key features" text={c.bullets.map((b) => "- " + b).join("\n")} copied={copied} onCopy={copy}>
                <ul>{c.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
              </Field>

              <Field id="tags" label="Tags" text={c.tags.join(", ")} copied={copied} onCopy={copy}>
                <div className="chips">{c.tags.map((t) => <span key={t}>{t}</span>)}</div>
              </Field>

              <Field id="seo" label="Search listing preview" text={`${c.seo.meta_title}\n${c.seo.meta_description}`} copied={copied} onCopy={copy}>
                <div className="serp">
                  <b>{c.seo.meta_title}</b>
                  <span>{c.seo.meta_description}</span>
                </div>
              </Field>

              <Field id="alt" label="Image alt text" text={c.alt_text} copied={copied} onCopy={copy}>
                <p>{c.alt_text}</p>
              </Field>

              <details className="seen">
                <summary>BLIP response ({result.seconds}s)</summary>
                <p className="cap">“{a.captions.plain}”</p>
                <dl>
                  {Object.entries(a.attributes).map(([k, v]) => (
                    <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
                  ))}
                </dl>
              
              </details>
            </article>
          )}
        </section>
      </main>
    </div>
  );
}

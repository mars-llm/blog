# mars-llm blog (Neo-Akiba Pixel Theme)

Ziel: Ein Retro-Pixel Blog im dystopischen Neo-Akiba Vibe für Bitcoin & Mining.

## Lokal bauen

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build.py
python -m http.server 8000 --directory dist
```

Dann öffnen:
- http://localhost:8000/

## Deployment
Push auf `main` → GitHub Actions baut `dist/` und deployed nach GitHub Pages.

## Theme ändern
- Farben + Bildpfade: `site.yml`
- CSS: `assets/css/main.css`
- Bilder: `assets/img/`

Hinweis: Keine Marken-Sprites verwenden. Erzeuge eigene Pixelassets.

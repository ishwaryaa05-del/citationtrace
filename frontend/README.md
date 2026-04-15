# CitationTrace Frontend

A static HTML/CSS/JS frontend for the CitationTrace SaaS platform — verified scholarly citation retrieval with RAG-powered synthesis.

## Structure

```
frontend/
└── index.html    # Single-file app (embedded CSS + JS)
```

## Features

- **Search interface** — accepts any research question
- **Synthesized Answer panel** — answer text with inline `[1]`, `[2]` citation markers rendered as blue superscript anchor links that scroll to the corresponding citation card
- **Verified Citations panel** — citation cards with title, authors, year, DOI link, confidence badge (green ≥0.6, yellow 0.35–0.6, red <0.35), and verified/unverified status
- **Audit Trail panel** — expandable table showing claim → source → confidence bar → status for full chain-of-evidence traceability
- **Demo mode** — if the backend is unreachable or returns an error, falls back to built-in demo data and shows a banner; the UI always works

## Deployment

### Local preview

Open `index.html` directly in a browser — no build step, no server required.

```bash
open index.html
# or
python3 -m http.server 3000 --directory .
# then visit http://localhost:3000
```

### Static hosting (any provider)

The entire app is a single `index.html` file. Deploy to:

**AWS S3 + CloudFront**
```bash
aws s3 sync . s3://your-bucket-name/ --exclude "README.md"
# Enable static website hosting on the bucket
# Point CloudFront distribution at the S3 origin
```

**Netlify**
```bash
# Drag-and-drop the frontend/ folder at app.netlify.com/drop
# or use CLI:
netlify deploy --dir . --prod
```

**Vercel**
```bash
vercel --prod
```

**GitHub Pages**
```
Push to a GitHub repo → Settings → Pages → Source: main / (root)
```

**Nginx / Apache**
Copy `index.html` to the document root (`/var/www/html/` or equivalent).

## Connecting to the Backend API

By default the frontend calls `http://localhost:8000/query` (POST). To point it at a deployed backend:

1. Open `index.html` in a text editor
2. Search for `http://localhost:8000/query`
3. Replace with your API endpoint URL, e.g.:
   ```
   https://api.citationtrace.io/query
   ```

The expected request format:
```json
POST /query
Content-Type: application/json

{ "query": "Your research question" }
```

Expected response shape:
```json
{
  "query": "...",
  "answer": "Full text with [1], [2] markers",
  "citations": [
    {
      "id": 1,
      "title": "Paper title",
      "authors": ["Author A", "Author B"],
      "year": 2024,
      "doi": "10.xxxx/...",
      "abstract_snippet": "Brief excerpt",
      "url": "https://...",
      "confidence_score": 0.82,
      "verified": true
    }
  ],
  "audit_trail": [
    {
      "claim": "Exact claim text",
      "source_id": 1,
      "confidence": 0.82,
      "status": "verified"
    }
  ],
  "total_claims": 6,
  "verified_claims": 6,
  "citation_accuracy": 1.0
}
```

If the backend returns an HTTP error or is unreachable, the frontend automatically falls back to demo data so the UI remains functional during development or outages.

## Browser Support

Tested in Chrome 120+, Firefox 121+, Safari 17+. Uses standard ES2020 features (`async/await`, optional chaining) — no polyfills needed for modern browsers. Fully responsive down to 375px viewport width.

## CORS Note

If hosting the frontend on a different origin from the backend, ensure the backend returns appropriate CORS headers:
```
Access-Control-Allow-Origin: https://your-frontend-domain.com
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

## Tech Stack

- Vanilla HTML5, CSS3, JavaScript (ES2020)
- No dependencies, no build step, no framework
- Inline SVG logo and icons
- System font stack (no external font requests)

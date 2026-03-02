# Personal Link Dashboard

A clean, minimal, local-first dashboard you can use as your browser new tab page.

## Stack

- **Backend:** Python standard library (`http.server`)
- **Database:** SQLite (`data/dashboard.db`) via built-in `sqlite3`
- **Frontend:** Vanilla HTML/CSS/JS

No external dependencies are required.

## Features

- Left sidebar with **panels** (each panel has its own categories and links)
- Center column for categories and links
- Right sidebar for quick **notes**
- Search links across all panels/categories (press Search/Enter)
- Add/edit/delete links with name, URL, and description
- Create/delete categories (category must be empty to delete)
- Create/delete panels
- Persistent SQLite storage

## Run locally

```bash
python3 server.py
```

Open:

- http://localhost:3000

## Deploy (open from anywhere)

This repo now includes deployment files for **Render**.

### Option A: One-click-ish with `render.yaml`

1. Push this repository to GitHub.
2. In Render: **New +** → **Blueprint**.
3. Select your repo.
4. Render will detect `render.yaml` and create the web service.
5. After deploy, open your public `https://<service>.onrender.com` URL.

### Option B: Docker deploy manually

- `Dockerfile` is included.
- Any host that supports Docker (Render, Fly.io, Railway, VPS) can run:

```bash
docker build -t personal-link-dashboard .
docker run -p 3000:3000 personal-link-dashboard
```

Then open `http://localhost:3000`.

## Important note about persistence

On free cloud instances, local SQLite disk may reset on redeploy/restart depending on provider settings.
For reliable long-term data, move DB to managed Postgres/MySQL or attach persistent volume.

## API endpoints

- `GET /healthz`
- `GET /api/dashboard`
- `GET /api/search?q=term`
- `POST /api/panels`
- `DELETE /api/panels/:id`
- `POST /api/categories`
- `DELETE /api/categories/:id`
- `POST /api/links`
- `PUT /api/links/:id`
- `DELETE /api/links/:id`
- `POST /api/notes`
- `PUT /api/notes/:id`
- `DELETE /api/notes/:id`

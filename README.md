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

## API endpoints

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

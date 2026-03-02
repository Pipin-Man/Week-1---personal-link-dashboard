import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(ROOT_DIR, 'public')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'dashboard.db')
PORT = int(os.environ.get('PORT', '3000'))

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute('PRAGMA foreign_keys = ON')


def init_db():
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS panels (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL UNIQUE,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS categories (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          panel_id INTEGER NOT NULL,
          name TEXT NOT NULL,
          sort_order INTEGER NOT NULL DEFAULT 0,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (panel_id, name),
          FOREIGN KEY (panel_id) REFERENCES panels(id) ON DELETE CASCADE
        )
        '''
    )

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS links (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          category_id INTEGER NOT NULL,
          name TEXT NOT NULL,
          url TEXT NOT NULL,
          description TEXT NOT NULL DEFAULT '',
          sort_order INTEGER NOT NULL DEFAULT 0,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
        '''
    )

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS notes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          content TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    conn.commit()

    # Basic migration path from older schema.
    category_cols = [row['name'] for row in conn.execute("PRAGMA table_info(categories)").fetchall()]
    link_cols = [row['name'] for row in conn.execute("PRAGMA table_info(links)").fetchall()]

    if 'panel_id' not in category_cols:
        conn.execute('ALTER TABLE categories ADD COLUMN panel_id INTEGER')
    if 'sort_order' not in category_cols:
        conn.execute('ALTER TABLE categories ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0')
    if 'description' not in link_cols:
        conn.execute("ALTER TABLE links ADD COLUMN description TEXT NOT NULL DEFAULT ''")
    if 'sort_order' not in link_cols:
        conn.execute('ALTER TABLE links ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0')

    # Ensure there is at least one panel before assigning categories.
    panel_count = conn.execute('SELECT COUNT(*) AS count FROM panels').fetchone()['count']
    if panel_count == 0:
        conn.execute('INSERT INTO panels (name) VALUES (?)', ('Main',))

    default_panel = conn.execute('SELECT id FROM panels ORDER BY id ASC LIMIT 1').fetchone()['id']
    conn.execute('UPDATE categories SET panel_id = ? WHERE panel_id IS NULL OR panel_id = 0', (default_panel,))
    conn.commit()

    panel_count = conn.execute('SELECT COUNT(*) AS count FROM panels').fetchone()['count']
    if panel_count == 0:
        panel_id = conn.execute('INSERT INTO panels (name) VALUES (?)', ('Main',)).lastrowid
        conn.execute('INSERT INTO categories (panel_id, name, sort_order) VALUES (?, ?, ?)', (panel_id, 'General', 0))
        conn.commit()


def json_response(handler, code, payload):
    body = json.dumps(payload).encode('utf-8')
    handler.send_response(code)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def empty_response(handler, code=204):
    handler.send_response(code)
    handler.end_headers()


def read_json(handler):
    try:
        content_length = int(handler.headers.get('Content-Length', '0'))
    except ValueError:
        return None
    data = handler.rfile.read(content_length) if content_length > 0 else b''
    if not data:
        return {}
    try:
        return json.loads(data.decode('utf-8'))
    except json.JSONDecodeError:
        return None


def parse_id(path, prefix):
    value = path.replace(prefix, '', 1)
    return int(value) if value.isdigit() else None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/dashboard':
            self.get_dashboard()
            return
        if parsed.path == '/api/search':
            self.search_links(parsed.query)
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        routes = {
            '/api/panels': self.create_panel,
            '/api/categories': self.create_category,
            '/api/links': self.create_link,
            '/api/notes': self.create_note,
        }
        if self.path in routes:
            routes[self.path]()
            return
        json_response(self, 404, {'error': 'Not found.'})

    def do_PUT(self):
        if self.path.startswith('/api/links/'):
            self.update_link()
            return
        if self.path.startswith('/api/notes/'):
            self.update_note()
            return
        json_response(self, 404, {'error': 'Not found.'})

    def do_DELETE(self):
        if self.path.startswith('/api/panels/'):
            self.delete_panel()
            return
        if self.path.startswith('/api/categories/'):
            self.delete_category()
            return
        if self.path.startswith('/api/links/'):
            self.delete_link()
            return
        if self.path.startswith('/api/notes/'):
            self.delete_note()
            return
        json_response(self, 404, {'error': 'Not found.'})

    def serve_static(self, path):
        if path == '/':
            path = '/index.html'
        full_path = os.path.abspath(os.path.join(PUBLIC_DIR, path.lstrip('/')))
        if not full_path.startswith(os.path.abspath(PUBLIC_DIR)) or not os.path.exists(full_path) or os.path.isdir(full_path):
            self.send_response(404)
            self.end_headers()
            return

        ext = os.path.splitext(full_path)[1]
        content_type = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
        }.get(ext, 'application/octet-stream')

        with open(full_path, 'rb') as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def get_dashboard(self):
        panels = [dict(r) for r in conn.execute('SELECT id, name FROM panels ORDER BY name ASC').fetchall()]
        categories = [
            dict(r)
            for r in conn.execute(
                'SELECT id, panel_id AS panelId, name, sort_order AS sortOrder FROM categories ORDER BY sort_order ASC, name ASC'
            ).fetchall()
        ]
        links = [
            dict(r)
            for r in conn.execute(
                'SELECT id, category_id AS categoryId, name, url, description, sort_order AS sortOrder '
                'FROM links ORDER BY sort_order ASC, name ASC'
            ).fetchall()
        ]
        notes = [dict(r) for r in conn.execute('SELECT id, content, created_at AS createdAt FROM notes ORDER BY created_at DESC').fetchall()]

        category_map = {}
        for category in categories:
            category_map[category['id']] = {**category, 'links': []}

        for link in links:
            item = category_map.get(link['categoryId'])
            if item:
                item['links'].append(link)

        payload = []
        for panel in panels:
            panel_categories = [c for c in category_map.values() if c['panelId'] == panel['id']]
            payload.append({'id': panel['id'], 'name': panel['name'], 'categories': panel_categories})

        json_response(self, 200, {'panels': payload, 'notes': notes})

    def search_links(self, query_string):
        params = dict(part.split('=', 1) for part in query_string.split('&') if '=' in part) if query_string else {}
        q = params.get('q', '').replace('+', ' ').strip()
        if not q:
            json_response(self, 200, [])
            return

        rows = conn.execute(
            'SELECT links.id, links.name, links.url, links.description, categories.name AS categoryName, panels.name AS panelName '
            'FROM links '
            'JOIN categories ON categories.id = links.category_id '
            'JOIN panels ON panels.id = categories.panel_id '
            'WHERE links.name LIKE ? OR links.description LIKE ? OR links.url LIKE ? '
            'ORDER BY links.name ASC',
            (f'%{q}%', f'%{q}%', f'%{q}%')
        ).fetchall()
        json_response(self, 200, [dict(r) for r in rows])

    def create_panel(self):
        data = read_json(self)
        if data is None:
            return json_response(self, 400, {'error': 'Invalid JSON.'})
        name = str(data.get('name', '')).strip()
        if not name:
            return json_response(self, 400, {'error': 'Panel name is required.'})

        try:
            cur = conn.execute('INSERT INTO panels (name) VALUES (?)', (name,))
            conn.commit()
            panel = conn.execute('SELECT id, name FROM panels WHERE id = ?', (cur.lastrowid,)).fetchone()
            json_response(self, 201, dict(panel))
        except sqlite3.IntegrityError:
            json_response(self, 409, {'error': 'Panel name must be unique.'})

    def delete_panel(self):
        panel_id = parse_id(self.path, '/api/panels/')
        if panel_id is None:
            return json_response(self, 400, {'error': 'Invalid panel ID.'})

        panel = conn.execute('SELECT id FROM panels WHERE id = ?', (panel_id,)).fetchone()
        if not panel:
            return json_response(self, 404, {'error': 'Panel not found.'})

        conn.execute('DELETE FROM panels WHERE id = ?', (panel_id,))
        conn.commit()
        empty_response(self)

    def create_category(self):
        data = read_json(self)
        if data is None:
            return json_response(self, 400, {'error': 'Invalid JSON.'})

        panel_id = data.get('panelId')
        name = str(data.get('name', '')).strip()
        if not isinstance(panel_id, int) or not name:
            return json_response(self, 400, {'error': 'Panel and category name are required.'})

        panel = conn.execute('SELECT id FROM panels WHERE id = ?', (panel_id,)).fetchone()
        if not panel:
            return json_response(self, 404, {'error': 'Panel not found.'})

        link_count = conn.execute('SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM categories WHERE panel_id = ?', (panel_id,)).fetchone()['next_order']

        try:
            cur = conn.execute(
                'INSERT INTO categories (panel_id, name, sort_order) VALUES (?, ?, ?)',
                (panel_id, name, link_count)
            )
            conn.commit()
            category = conn.execute(
                'SELECT id, panel_id AS panelId, name, sort_order AS sortOrder FROM categories WHERE id = ?',
                (cur.lastrowid,),
            ).fetchone()
            json_response(self, 201, dict(category))
        except sqlite3.IntegrityError:
            json_response(self, 409, {'error': 'Category already exists in this panel.'})

    def delete_category(self):
        category_id = parse_id(self.path, '/api/categories/')
        if category_id is None:
            return json_response(self, 400, {'error': 'Invalid category ID.'})

        category = conn.execute('SELECT id FROM categories WHERE id = ?', (category_id,)).fetchone()
        if not category:
            return json_response(self, 404, {'error': 'Category not found.'})

        has_links = conn.execute('SELECT COUNT(*) AS count FROM links WHERE category_id = ?', (category_id,)).fetchone()['count']
        if has_links > 0:
            return json_response(self, 409, {'error': 'Category must be empty before deletion.'})

        conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        conn.commit()
        empty_response(self)

    def create_link(self):
        data = read_json(self)
        if data is None:
            return json_response(self, 400, {'error': 'Invalid JSON.'})

        category_id = data.get('categoryId')
        name = str(data.get('name', '')).strip()
        url = str(data.get('url', '')).strip()
        description = str(data.get('description', '')).strip()

        if not isinstance(category_id, int) or not name or not url:
            return json_response(self, 400, {'error': 'Category, name and URL are required.'})

        category = conn.execute('SELECT id FROM categories WHERE id = ?', (category_id,)).fetchone()
        if not category:
            return json_response(self, 404, {'error': 'Category not found.'})

        next_order = conn.execute('SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM links WHERE category_id = ?', (category_id,)).fetchone()['next_order']
        cur = conn.execute(
            'INSERT INTO links (category_id, name, url, description, sort_order) VALUES (?, ?, ?, ?, ?)',
            (category_id, name, url, description, next_order)
        )
        conn.commit()
        link = conn.execute(
            'SELECT id, category_id AS categoryId, name, url, description, sort_order AS sortOrder FROM links WHERE id = ?',
            (cur.lastrowid,)
        ).fetchone()
        json_response(self, 201, dict(link))

    def update_link(self):
        link_id = parse_id(self.path, '/api/links/')
        if link_id is None:
            return json_response(self, 400, {'error': 'Invalid link ID.'})

        data = read_json(self)
        if data is None:
            return json_response(self, 400, {'error': 'Invalid JSON.'})

        category_id = data.get('categoryId')
        name = str(data.get('name', '')).strip()
        url = str(data.get('url', '')).strip()
        description = str(data.get('description', '')).strip()

        if not isinstance(category_id, int) or not name or not url:
            return json_response(self, 400, {'error': 'Category, name and URL are required.'})

        link = conn.execute('SELECT id FROM links WHERE id = ?', (link_id,)).fetchone()
        if not link:
            return json_response(self, 404, {'error': 'Link not found.'})

        category = conn.execute('SELECT id FROM categories WHERE id = ?', (category_id,)).fetchone()
        if not category:
            return json_response(self, 404, {'error': 'Category not found.'})

        conn.execute(
            'UPDATE links SET category_id = ?, name = ?, url = ?, description = ? WHERE id = ?',
            (category_id, name, url, description, link_id)
        )
        conn.commit()
        updated = conn.execute(
            'SELECT id, category_id AS categoryId, name, url, description, sort_order AS sortOrder FROM links WHERE id = ?',
            (link_id,)
        ).fetchone()
        json_response(self, 200, dict(updated))

    def delete_link(self):
        link_id = parse_id(self.path, '/api/links/')
        if link_id is None:
            return json_response(self, 400, {'error': 'Invalid link ID.'})

        link = conn.execute('SELECT id FROM links WHERE id = ?', (link_id,)).fetchone()
        if not link:
            return json_response(self, 404, {'error': 'Link not found.'})

        conn.execute('DELETE FROM links WHERE id = ?', (link_id,))
        conn.commit()
        empty_response(self)

    def create_note(self):
        data = read_json(self)
        if data is None:
            return json_response(self, 400, {'error': 'Invalid JSON.'})
        content = str(data.get('content', '')).strip()
        if not content:
            return json_response(self, 400, {'error': 'Note content is required.'})

        cur = conn.execute('INSERT INTO notes (content) VALUES (?)', (content,))
        conn.commit()
        note = conn.execute('SELECT id, content, created_at AS createdAt FROM notes WHERE id = ?', (cur.lastrowid,)).fetchone()
        json_response(self, 201, dict(note))

    def update_note(self):
        note_id = parse_id(self.path, '/api/notes/')
        if note_id is None:
            return json_response(self, 400, {'error': 'Invalid note ID.'})

        data = read_json(self)
        if data is None:
            return json_response(self, 400, {'error': 'Invalid JSON.'})
        content = str(data.get('content', '')).strip()
        if not content:
            return json_response(self, 400, {'error': 'Note content is required.'})

        note = conn.execute('SELECT id FROM notes WHERE id = ?', (note_id,)).fetchone()
        if not note:
            return json_response(self, 404, {'error': 'Note not found.'})

        conn.execute('UPDATE notes SET content = ? WHERE id = ?', (content, note_id))
        conn.commit()
        updated = conn.execute('SELECT id, content, created_at AS createdAt FROM notes WHERE id = ?', (note_id,)).fetchone()
        json_response(self, 200, dict(updated))

    def delete_note(self):
        note_id = parse_id(self.path, '/api/notes/')
        if note_id is None:
            return json_response(self, 400, {'error': 'Invalid note ID.'})

        note = conn.execute('SELECT id FROM notes WHERE id = ?', (note_id,)).fetchone()
        if not note:
            return json_response(self, 404, {'error': 'Note not found.'})

        conn.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        conn.commit()
        empty_response(self)


if __name__ == '__main__':
    init_db()
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f'Dashboard running at http://localhost:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        conn.close()

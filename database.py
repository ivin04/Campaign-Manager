import sqlite3
from pathlib import Path
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "campaign.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=10,
    )

    conn.row_factory = sqlite3.Row

    # SQLite puede tener varias conexiones simultáneas.
    # WAL permite que las lecturas no bloqueen las escrituras
    # y viceversa en la mayoría de los casos.
    conn.execute("PRAGMA journal_mode=WAL")

    # Esperar hasta 10 segundos antes de lanzar
    # "database is locked".
    conn.execute("PRAGMA busy_timeout=10000")

    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def init_db():

    with get_conn() as conn:

        conn.executescript("""
        CREATE TABLE IF NOT EXISTS campaign (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL,
            system TEXT NOT NULL DEFAULT 'D&D 5e 2014',
            tone TEXT,
            current_location_id INTEGER,
            current_session_id INTEGER,
            summary TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'npc',
            description TEXT DEFAULT '',
            personality TEXT DEFAULT '',
            goals TEXT DEFAULT '',
            knowledge TEXT DEFAULT '',
            secrets TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            location TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            kind TEXT DEFAULT '',
            description TEXT DEFAULT '',
            inhabitants TEXT DEFAULT '',
            secrets TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS factions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            goals TEXT DEFAULT '',
            resources TEXT DEFAULT '',
            allies TEXT DEFAULT '',
            enemies TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            description TEXT DEFAULT '',
            clues TEXT DEFAULT '',
            related_npcs TEXT DEFAULT '',
            consequences TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            owner TEXT DEFAULT '',
            location TEXT DEFAULT '',
            significance TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            session INTEGER,
            event_type TEXT DEFAULT '',
            description TEXT NOT NULL,
            consequences TEXT DEFAULT '',
            secret INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            relation TEXT NOT NULL,
            strength INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            UNIQUE(source_type, source_id, target_type, target_id, relation)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER NOT NULL UNIQUE,
            title TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            start_location TEXT DEFAULT '',
            end_location TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_characters_name
            ON characters(name);

        CREATE INDEX IF NOT EXISTS idx_locations_name
            ON locations(name);

        CREATE INDEX IF NOT EXISTS idx_factions_name
            ON factions(name);

        CREATE INDEX IF NOT EXISTS idx_quests_name
            ON quests(name);

        CREATE INDEX IF NOT EXISTS idx_events_title
            ON events(title);

        CREATE INDEX IF NOT EXISTS idx_events_session
            ON events(session);
        """)

        row = conn.execute(
            "SELECT id FROM campaign WHERE id=1"
        ).fetchone()

        if not row:
            conn.execute("""
                INSERT INTO campaign
                    (id, name, system, tone, summary)
                VALUES (?, ?, ?, ?, ?)
            """, (
                1,
                "Nueva campaña",
                "D&D 5e 2014",
                "Serio, oscuro y épico, con toques de humor natural",
                ""
            ))


def rows(query, params=()):

    with get_conn() as conn:

        return [
            dict(row)
            for row in conn.execute(
                query,
                params
            ).fetchall()
        ]


def one(query, params=()):

    with get_conn() as conn:

        row = conn.execute(
            query,
            params
        ).fetchone()

        return dict(row) if row else None


def execute(query, params=()):

    with get_conn() as conn:

        cur = conn.execute(
            query,
            params
        )

        last_id = cur.lastrowid

        return last_id
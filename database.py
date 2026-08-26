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

    # Permitir lecturas mientras se realizan escrituras.
    conn.execute("PRAGMA journal_mode=WAL")

    # Esperar hasta 10 segundos si SQLite está ocupado.
    conn.execute("PRAGMA busy_timeout=10000")

    # Activar integridad referencial.
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

        -- ============================================================
        -- CAMPAIGN
        -- ============================================================

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


        -- ============================================================
        -- NUEVO MODELO DE DOMINIO
        -- ENTITY
        -- ============================================================

        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            entity_type TEXT NOT NULL DEFAULT '',

            description TEXT DEFAULT '',

            notes TEXT DEFAULT '',

            active INTEGER NOT NULL DEFAULT 1,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );


        CREATE INDEX IF NOT EXISTS idx_entities_name
            ON entities(name);

        CREATE INDEX IF NOT EXISTS idx_entities_type
            ON entities(entity_type);


        -- ============================================================
        -- ITEMS
        -- Definición de un tipo de objeto.
        -- ============================================================

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL UNIQUE,

            description TEXT DEFAULT '',

            significance TEXT DEFAULT '',

            unique_item INTEGER NOT NULL DEFAULT 0,

            notes TEXT DEFAULT '',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );


        CREATE INDEX IF NOT EXISTS idx_items_name
            ON items(name);


        -- ============================================================
        -- ITEM INSTANCES
        -- Copias físicas concretas de un Item.
        -- ============================================================

        CREATE TABLE IF NOT EXISTS item_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            item_id INTEGER NOT NULL,

            instance_number INTEGER NOT NULL DEFAULT 1,

            owner_id INTEGER,

            location_id INTEGER,

            condition TEXT DEFAULT '',

            notes TEXT DEFAULT '',

            active INTEGER NOT NULL DEFAULT 1,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (item_id)
                REFERENCES items(id)
                ON DELETE CASCADE,

            FOREIGN KEY (owner_id)
                REFERENCES entities(id)
                ON DELETE SET NULL,

            FOREIGN KEY (location_id)
                REFERENCES entities(id)
                ON DELETE SET NULL,

            UNIQUE(item_id, instance_number)
        );


        CREATE INDEX IF NOT EXISTS idx_item_instances_item
            ON item_instances(item_id);

        CREATE INDEX IF NOT EXISTS idx_item_instances_owner
            ON item_instances(owner_id);

        CREATE INDEX IF NOT EXISTS idx_item_instances_location
            ON item_instances(location_id);


        -- ============================================================
        -- RESOURCES
        -- ============================================================

        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL UNIQUE,

            resource_type TEXT NOT NULL DEFAULT 'generic',

            unit TEXT DEFAULT '',

            notes TEXT DEFAULT '',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );


        CREATE INDEX IF NOT EXISTS idx_resources_name
            ON resources(name);


        -- ============================================================
        -- RESOURCE BALANCES
        -- ============================================================

        CREATE TABLE IF NOT EXISTS resource_balances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            resource_id INTEGER NOT NULL,

            owner_id INTEGER NOT NULL,

            amount REAL NOT NULL DEFAULT 0,

            notes TEXT DEFAULT '',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (resource_id)
                REFERENCES resources(id)
                ON DELETE CASCADE,

            FOREIGN KEY (owner_id)
                REFERENCES entities(id)
                ON DELETE CASCADE,

            UNIQUE(resource_id, owner_id)
        );


        CREATE INDEX IF NOT EXISTS idx_resource_balances_resource
            ON resource_balances(resource_id);

        CREATE INDEX IF NOT EXISTS idx_resource_balances_owner
            ON resource_balances(owner_id);


        -- ============================================================
        -- RELATIONS
        -- ============================================================

        CREATE TABLE IF NOT EXISTS relations (
            id TEXT PRIMARY KEY,

            subject_id INTEGER NOT NULL,

            relation_type TEXT NOT NULL,

            target_id INTEGER NOT NULL,

            metadata TEXT,

            active INTEGER NOT NULL DEFAULT 1,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (subject_id)
                REFERENCES entities(id)
                ON DELETE CASCADE,

            FOREIGN KEY (target_id)
                REFERENCES entities(id)
                ON DELETE CASCADE
        );


        CREATE INDEX IF NOT EXISTS idx_relations_subject
            ON relations(subject_id);

        CREATE INDEX IF NOT EXISTS idx_relations_target
            ON relations(target_id);

        CREATE INDEX IF NOT EXISTS idx_relations_type
            ON relations(relation_type);


        -- ============================================================
        -- EVENTS
        -- ============================================================

        CREATE TABLE IF NOT EXISTS world_events (
            id TEXT PRIMARY KEY,

            event_type TEXT NOT NULL,

            title TEXT NOT NULL,

            description TEXT DEFAULT '',

            consequences TEXT DEFAULT '',

            session_id INTEGER,

            secret INTEGER NOT NULL DEFAULT 0,

            metadata TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );


        CREATE INDEX IF NOT EXISTS idx_world_events_session
            ON world_events(session_id);

        CREATE INDEX IF NOT EXISTS idx_world_events_type
            ON world_events(event_type);


        -- ============================================================
        -- SESSIONS
        -- ============================================================

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


        CREATE INDEX IF NOT EXISTS idx_sessions_number
            ON sessions(number);


        -- ============================================================
        -- CAMPAIGN DEFAULT
        -- ============================================================

        """)

        row = conn.execute(
            "SELECT id FROM campaign WHERE id=1"
        ).fetchone()

        if not row:

            conn.execute(
                """
                INSERT INTO campaign
                    (id, name, system, tone, summary)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    1,
                    "Nueva campaña",
                    "D&D 5e 2014",
                    "Serio, oscuro y épico, con toques de humor natural",
                    "",
                ),
            )


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

        return cur.lastrowid
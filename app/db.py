import unicodedata

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.paths import DATA_ROOT

DB_PATH = DATA_ROOT / 'production.db'
engine = create_engine(f'sqlite:///{DB_PATH.as_posix()}', connect_args={'check_same_thread': False})
def normalize_search(value):
    text = unicodedata.normalize('NFKD', str(value or '')).casefold()
    return ''.join(char for char in text if not unicodedata.combining(char))


@event.listens_for(engine, 'connect')
def configure_sqlite(connection, _):
    connection.create_function('fluxo_search', 1, normalize_search, deterministic=True)


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db():
    from app import (  # noqa: F401
        art_editor,
        dtf_hotfolder,
        dtf_studio,
        models,
        print_console,
        printer_links,
        stations,
    )
    Base.metadata.create_all(bind=engine)
    # Upgrade compatível com a estrutura 0.1 se houver um DB existente.
    additions = {
        'printers': {
            'watch_folder': 'TEXT',
            'workstation': 'VARCHAR(120)',
            'firmware': 'VARCHAR(120)',
            'printexp_version': 'VARCHAR(120)',
        },
        'orders': {'printer_id': 'VARCHAR(64)'},
    }
    with engine.begin() as conn:
        inspector = inspect(conn)
        for table, new_columns in additions.items():
            present = {c['name'] for c in inspector.get_columns(table)}
            for col, sqltype in new_columns.items():
                if col not in present:
                    conn.exec_driver_sql(f'ALTER TABLE {table} ADD COLUMN {col} {sqltype}')

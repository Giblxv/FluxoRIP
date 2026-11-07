from pathlib import Path
from app.paths import DATA_ROOT
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = DATA_ROOT / 'production.db'
engine = create_engine(f'sqlite:///{DB_PATH.as_posix()}', connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db():
    from app import models, art_editor, print_console, stations, printer_links, dtf_studio, dtf_hotfolder  # noqa: F401
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

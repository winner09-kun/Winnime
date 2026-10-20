"""Recreate the explicitly selected official sources on a fresh local install.

Run from the project root: python -m backend.import_official_sources
Availability is ultimately controlled by the YouTube embed player.
"""
import json
from pathlib import Path
from sqlalchemy import select
from .app.core.database import Base, engine, Session
from .app.models import Source
from .app.schemas import SourceInput

def main():
    Base.metadata.create_all(engine)
    added = 0
    with Session() as db:
        for record in json.loads(Path(__file__).with_name('official_sources.json').read_text(encoding='utf-8')):
            source = SourceInput.model_validate(record)
            exists = db.scalar(select(Source).where(Source.anime_id==source.anime_id,Source.episode==source.episode,Source.provider==source.provider,Source.url==source.url))
            if exists is None:
                db.add(Source(**source.model_dump(exclude={'authorized'})))
                added += 1
        db.commit()
    print(f'{added} official source(s) added.')

if __name__ == '__main__':
    main()

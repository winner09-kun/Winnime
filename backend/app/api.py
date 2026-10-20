import time
import asyncio
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from .core.database import get_db
from .models import Watchlist, History, Source, Setting
from .schemas import WatchInput, WatchPatch, HistoryInput, SourceInput, SettingsInput
from .repositories import rows, serialize
from .services import metadata, zen

router = APIRouter(prefix='/api')

@router.get('/health')
def health(): return {'status':'ok'}

@router.get('/anime/{kind}', response_model=dict)
async def anime_route(kind: str, page: int=Query(1, ge=1, le=1000), search: str|None=Query(None, max_length=200), genre: str|None=None, year: int|None=None, season: Literal['WINTER','SPRING','SUMMER','FALL']|None=None, format: Literal['TV','MOVIE','OVA','ONA','SPECIAL','TV_SHORT','MUSIC']|None=None, status: Literal['RELEASING','FINISHED','NOT_YET_RELEASED','CANCELLED','HIATUS']|None=None, sort: Literal['POPULARITY_DESC','SCORE_DESC','START_DATE_DESC','TITLE_ROMAJI']='POPULARITY_DESC'):
    if kind.isdigit(): return await metadata.detail(int(kind))
    if kind not in ('trending','popular','seasonal','search','recent'): raise HTTPException(404)
    return await metadata.catalog(kind,page,search,genre,year,season,format,status,sort)

@router.get('/anime/{anime_id}/recommendations')
async def recommendations(anime_id:int):
    return {'items':(await metadata.detail(anime_id))['anime']['recommendations']}

@router.get('/anime/{anime_id}/episodes')
async def episodes(anime_id:int, page:int=Query(1,ge=1), db:Session=Depends(get_db)):
    sources = db.scalars(select(Source).where(Source.anime_id==anime_id,Source.available==True)).all()
    zen_error = None
    try:
        items = zen.episodes(await zen.lookup(anime_id), anime_id)
        if items:
            numbers = {s.episode for s in sources}
            for item in items:
                item['playable'] = item['playable'] or item['number'] in numbers
            existing = {item['number'] for item in items}
            items += [{'number': n, 'title': None, 'playable': True, 'configured': True}
                      for n in numbers - existing]
            items.sort(key=lambda item: item['number'])
            return {'items': items if page == 1 else [], 'has_next': False, 'provider': 'Zen'}
    except HTTPException as exc:
        zen_error = exc.detail
    try:
        try:
            result = await asyncio.wait_for(metadata.episodes(anime_id,page), timeout=20)
        except TimeoutError:
            raise HTTPException(503, zen_error or 'Penyedia episode tidak merespons. Coba lagi nanti.') from None
    except HTTPException as exc:
        if not sources or exc.status_code != 503:
            raise
        result = {'items': [], 'has_next': False, 'note': 'Metadata episode belum tersedia. Menampilkan sumber video yang terhubung.'}
    numbers = {s.episode for s in sources}
    result['items'] = [{**e, 'playable':e['number'] in numbers} for e in result['items']]
    if page==1:
        existing = {e['number'] for e in result['items']}
        result['items'] += [{'number':n,'title':None,'playable':True,'configured':True} for n in numbers-existing]
        result['items'].sort(key=lambda e:e['number'])
    if zen_error:
        result['note'] = zen_error
    return result

@router.get('/episodes/{episode_id}/sources')
async def episode_sources(episode_id:str, db:Session=Depends(get_db)):
    try: anime_id, episode = map(int,episode_id.split(':'))
    except ValueError: raise HTTPException(422,'Episode ID must be anime_id:episode_number')
    if anime_id < 1 or episode < 1:
        raise HTTPException(422, 'Anime ID and episode must be positive')
    local = [serialize(s) for s in db.scalars(select(Source).where(Source.anime_id==anime_id,Source.episode==episode,Source.available==True)).all()]
    try:
        return zen.sources(await zen.lookup(anime_id), anime_id, episode) + local
    except HTTPException:
        if local:
            return local
        raise

@router.get('/sources')
def sources(db:Session=Depends(get_db)): return [serialize(s) for s in rows(db,Source)]

@router.post('/sources', status_code=201)
def add_source(body:SourceInput, db:Session=Depends(get_db)):
    row = Source(**body.model_dump(exclude={'authorized'}))
    db.add(row); db.commit(); db.refresh(row)
    return serialize(row)

@router.delete('/sources/{source_id}', status_code=204)
def remove_source(source_id:int, db:Session=Depends(get_db)):
    row=db.get(Source,source_id)
    if not row: raise HTTPException(404)
    db.delete(row); db.commit()
    return Response(status_code=204)

@router.get('/watchlist')
def watchlist(db:Session=Depends(get_db)): return [serialize(w) for w in rows(db,Watchlist,Watchlist.updated_at.desc())]

@router.post('/watchlist', status_code=201)
def add_watch(body:WatchInput, db:Session=Depends(get_db)):
    row=db.merge(Watchlist(**body.model_dump(),updated_at=time.time()))
    db.commit(); return serialize(row)

@router.patch('/watchlist/{anime_id}')
def patch_watch(anime_id:int, body:WatchPatch, db:Session=Depends(get_db)):
    row=db.get(Watchlist,anime_id)
    if not row: raise HTTPException(404)
    row.status=body.status; row.updated_at=time.time(); db.commit()
    return serialize(row)

@router.delete('/watchlist/{anime_id}',status_code=204)
def delete_watch(anime_id:int, db:Session=Depends(get_db)):
    row=db.get(Watchlist,anime_id)
    if not row: raise HTTPException(404)
    db.delete(row); db.commit(); return Response(status_code=204)

@router.get('/history')
def history(db:Session=Depends(get_db)): return [serialize(h) for h in rows(db,History,History.updated_at.desc())]

@router.post('/history')
def save_history(body:HistoryInput, db:Session=Depends(get_db)):
    row=db.merge(History(**body.model_dump(), episode_id=f'{body.anime_id}:{body.episode}',updated_at=time.time()))
    db.commit(); return serialize(row)

@router.delete('/history',status_code=204)
def clear_history(db:Session=Depends(get_db)):
    db.execute(delete(History)); db.commit(); return Response(status_code=204)

@router.delete('/history/{episode_id}',status_code=204)
def delete_history(episode_id:str, db:Session=Depends(get_db)):
    row=db.get(History,episode_id)
    if not row: raise HTTPException(404)
    db.delete(row); db.commit(); return Response(status_code=204)

@router.get('/settings',response_model=SettingsInput)
def settings(db:Session=Depends(get_db)):
    row=db.get(Setting,1)
    return row.data if row else SettingsInput().model_dump()

@router.patch('/settings',response_model=SettingsInput)
def patch_settings(body:SettingsInput, db:Session=Depends(get_db)):
    old=db.get(Setting,1)
    data={**(old.data if old else SettingsInput().model_dump()),**body.model_dump(exclude_unset=True)}
    db.merge(Setting(id=1,data=data)); db.commit(); return data

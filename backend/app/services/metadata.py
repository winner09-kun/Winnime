import asyncio
import hashlib
import html
import json
import logging
import re
import time
from datetime import datetime, timezone
import httpx
from fastapi import HTTPException
from ..core.database import Session
from ..core.config import config
from ..models import Cache
from sqlalchemy import select
from ..schemas import Anime

log = logging.getLogger('kaze.metadata')
FIELDS = '''id idMal title { romaji english native } coverImage { extraLarge } bannerImage description averageScore seasonYear season genres format status episodes duration studios(isMain: true) { nodes { name } } externalLinks { site url type } nextAiringEpisode { episode airingAt }'''
DETAIL = '''characters(perPage: 12, sort: ROLE) { nodes { name { full } image { large } } } relations { edges { relationType node { id type title { romaji english } coverImage { extraLarge } format } } } recommendations(perPage: 12, sort: RATING_DESC) { nodes { mediaRecommendation { id title { romaji english } coverImage { extraLarge } averageScore genres format episodes } } }'''
locks: dict[str, asyncio.Lock] = {}

async def request(url, payload=None):
    async with httpx.AsyncClient(timeout=20) as client:
        for attempt in range(3):
            try:
                response = await (client.post(url, json=payload) if payload else client.get(url))
                response.raise_for_status()
                data = response.json()
                if data.get('errors'):
                    raise ValueError('Metadata provider returned an error')
                return data
            except (httpx.HTTPError, ValueError) as exc:
                if isinstance(exc, httpx.HTTPStatusError):
                    code = exc.response.status_code
                    if 400 <= code < 500 and code != 429:
                        raise
                    if code == 429:
                        retry_after = exc.response.headers.get('Retry-After', '60')
                        # Let cached content serve long provider cooldowns.
                        if not retry_after.isdigit() or int(retry_after) > 15:
                            raise
                        await asyncio.sleep(int(retry_after))
                if attempt == 2:
                    raise
                await asyncio.sleep(0.7 * (2 ** attempt))

async def cached(key, fetch):
    key = hashlib.sha256(key.encode()).hexdigest()
    lock = locks.setdefault(key, asyncio.Lock())
    async with lock:
        with Session() as db:
            row = db.get(Cache, key)
            old = row.data if row else None
            if row and time.time() - row.updated_at < config.cache_ttl:
                return {**row.data, 'cached': True}
        try:
            data = await fetch()
            with Session() as db:
                db.merge(Cache(key=key, data=data, updated_at=time.time()))
                db.commit()
            return data
        except Exception as exc:
            log.warning(json.dumps({'event': 'metadata_request_failed', 'type': type(exc).__name__}))
            if old:
                return {**old, 'stale': True}
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(503, 'Layanan metadata sedang tidak tersedia. Coba lagi sebentar.') from exc

def normalize(m):
    return Anime(
        id=m['id'], mal_id=m.get('idMal'), title=m['title'].get('english') or m['title'].get('romaji') or 'Untitled',
        titles=list(dict.fromkeys(t for t in m['title'].values() if t)),
        cover=(m.get('coverImage') or {}).get('extraLarge'), banner=m.get('bannerImage'),
        description=html.unescape(re.sub('<[^>]+>', '', m.get('description') or '')),
        score=m['averageScore'] / 10 if m.get('averageScore') else None,
        year=m.get('seasonYear'), season=m.get('season'), genres=m.get('genres') or [],
        format=m.get('format'), status=m.get('status'), episodes=m.get('episodes'), duration=m.get('duration'),
        studios=[s['name'] for s in (m.get('studios') or {}).get('nodes', [])],
        links=[x for x in m.get('externalLinks', []) if x['type'] == 'STREAMING' and x['url'].startswith('https://')],
        next_episode=m.get('nextAiringEpisode'),
        characters=[{'name': c['name']['full'], 'image': c['image']['large']} for c in (m.get('characters') or {}).get('nodes', [])],
        relations=[{**normalize(e['node']).model_dump(), 'relation': e['relationType']} for e in (m.get('relations') or {}).get('edges', []) if e['node'].get('type') == 'ANIME'],
        recommendations=[normalize(r['mediaRecommendation']).model_dump() for r in (m.get('recommendations') or {}).get('nodes', []) if r.get('mediaRecommendation')],
    )

async def catalog(kind='search', page=1, search=None, genre=None, year=None, season=None, format=None, status=None, sort='POPULARITY_DESC'):
    args = {'type': 'ANIME', 'isAdult': False, 'sort': [sort]}
    if kind == 'trending': args['sort'] = ['TRENDING_DESC']
    if kind in ('seasonal', 'recent'):
        now = datetime.now(timezone.utc)
        args.update(seasonYear=now.year, season=['WINTER', 'SPRING', 'SUMMER', 'FALL'][(now.month-1)//3])
        if kind == 'recent':
            args['sort'] = ['START_DATE_DESC']
            args['status_in'] = ['RELEASING', 'FINISHED']
    if search: args['search'] = search
    if genre: args['genre'] = genre
    if year: args['seasonYear'] = year
    if season: args['season'] = season
    if format: args['format'] = format
    if status: args['status'] = status
    types = {'type':'MediaType', 'isAdult':'Boolean', 'sort':'[MediaSort]', 'search':'String', 'genre':'String', 'seasonYear':'Int', 'season':'MediaSeason', 'format':'MediaFormat', 'status':'MediaStatus', 'status_in':'[MediaStatus]'}
    declarations = ', '.join('$'+k+':'+types[k] for k in args)
    arguments = ', '.join(k+':$'+k for k in args)
    query = 'query($page:Int, '+declarations+') { Page(page:$page, perPage:18) { pageInfo { hasNextPage currentPage } media('+arguments+') { '+FIELDS+' } } }'
    async def fetch():
        data = (await request('https://graphql.anilist.co', {'query': query, 'variables': {**args, 'page':page}}))['data']['Page']
        return {'items': [normalize(m).model_dump() for m in data['media']], 'has_next':data['pageInfo']['hasNextPage'], 'page':page}
    return await cached(json.dumps({'args':args, 'page':page}, sort_keys=True), fetch)

async def detail(anime_id):
    async def fetch():
        try:
            m = (await request('https://graphql.anilist.co', {'query':'query($id:Int!) { Media(id:$id, type:ANIME) { '+FIELDS+' '+DETAIL+' } }', 'variables':{'id':anime_id}}))['data']['Media']
        except (httpx.HTTPError, ValueError):
            # Prefer a complete cached detail. Only fall back using a verified
            # AniList -> MAL mapping already received in a catalog response.
            with Session() as db:
                old = db.get(Cache, hashlib.sha256(('detail:'+str(anime_id)).encode()).hexdigest())
                if old: raise
                known = None
                for row in db.scalars(select(Cache)):
                    known = next((a for a in row.data.get('items',[]) if a.get('id')==anime_id and a.get('mal_id')), None)
                    if known: break
            if not known: raise
            j = (await request(f'https://api.jikan.moe/v4/anime/{known["mal_id"]}/full'))['data']
            fallback = {**known, 'description':j.get('synopsis') or known.get('description',''), 'episodes':j.get('episodes'), 'score':j.get('score'), 'studios':[s['name'] for s in j.get('studios',[])], 'links':[{'site':s['name'],'url':s['url']} for s in j.get('streaming',[]) if s['url'].startswith('https://')]}
            return {'anime':Anime(**fallback).model_dump(), 'provider':'jikan'}
        if not m: raise HTTPException(404, 'Anime tidak ditemukan')
        return {'anime':normalize(m).model_dump()}
    return await cached('detail:'+str(anime_id), fetch)

async def episodes(anime_id, page=1):
    anime = (await detail(anime_id))['anime']
    async def fetch():
        if not anime['mal_id']:
            return {'items':[], 'has_next':False, 'note':'Metadata episode belum tersedia.'}
        try:
            data = await request(f'https://api.jikan.moe/v4/anime/{anime["mal_id"]}/episodes?page={page}')
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {'items': [], 'has_next': False, 'note': 'Metadata episode belum tersedia di Jikan.'}
            raise
        return {'items':[{'number':e['mal_id'], 'title':e.get('title'), 'aired':e.get('aired'), 'filler':e.get('filler',False)} for e in data['data']], 'has_next':data.get('pagination',{}).get('has_next_page',False)}
    return await cached(f'episodes:{anime_id}:{page}', fetch)

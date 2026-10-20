"""Resolve public Zen episode data by verified AniList ID, never by title alone."""
import asyncio
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from . import metadata

BASE = 'https://api.anizen.tr'
slugs: dict[int, str] = {}

def embed_url(value):
    if not isinstance(value, str):
        return None
    try:
        url = urlsplit(value)
        if url.scheme == 'https' and url.hostname == 'api.anizen.tr' and not url.username and not url.password and url.port in (None, 443) and url.path.startswith('/player/'):
            return value
    except ValueError:
        pass
    return None

async def lookup(anime_id):
    try:
        async with asyncio.timeout(35):
            anime = (await metadata.detail(anime_id))['anime']
            def matches(data):
                if data.get('anilistId') is not None:
                    return str(data['anilistId']) == str(anime_id)
                return bool(anime.get('mal_id')) and str(data.get('malId')) == str(anime['mal_id'])
            async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
                async def get(path, params):
                    response = await client.get(BASE + path, params=params)
                    response.raise_for_status()
                    body = response.json()
                    if body.get('success') is not True:
                        raise ValueError('Zen failed')
                    return body['results']['data']
                failed = False
                async def info(slug):
                    nonlocal failed
                    try:
                        data = await get('/api/info', {'id': slug})
                        if isinstance(data, dict) and matches(data):
                            return data
                    except (httpx.HTTPError, ValueError, KeyError, TypeError):
                        failed = True
                    return None

                if anime_id in slugs:
                    data = await info(slugs[anime_id])
                    if data is not None:
                        return data
                    slugs.pop(anime_id, None)
                titles = list(dict.fromkeys([anime['title'], *anime.get('titles', [])]))
                seen = set()
                for title in titles[:3]:
                    try:
                        candidates = await get('/api/search', {'keyword': title})
                        if not isinstance(candidates, list):
                            raise ValueError('Invalid search response')
                    except (httpx.HTTPError, ValueError, KeyError, TypeError):
                        failed = True
                        continue
                    ids = [c['id'] for c in candidates[:12]
                           if isinstance(c, dict) and isinstance(c.get('id'), str) and c['id'] not in seen]
                    seen.update(ids)
                    # A broken or irrelevant first result must not hide the correct season.
                    for start in range(0, len(ids), 3):
                        batch = ids[start:start + 3]
                        results = await asyncio.gather(*(info(slug) for slug in batch))
                        for slug, data in zip(batch, results):
                            if data is not None:
                                if len(slugs) >= 128:
                                    slugs.pop(next(iter(slugs)))
                                slugs[anime_id] = slug
                                return data
                if failed:
                    raise ValueError('Incomplete provider search')
                return None
    except (httpx.HTTPError, ValueError, KeyError, TypeError, TimeoutError, HTTPException):
        raise HTTPException(503, 'Sumber episode Zen belum dapat dimuat. Coba lagi nanti.') from None

def sources(data, anime_id, number):
    result = []
    for episode in (data or {}).get('episodes', {}).get('episodes', []):
        if str(episode.get('episode_no')) != str(number):
            continue
        for language in ('sub', 'dub'):
            for server in (episode.get('streams') or {}).get(language, []):
                url = embed_url(server.get('embed'))
                if url:
                    result.append({'id': -(len(result) + 1), 'anime_id': anime_id, 'episode': number,
                                   'provider': 'embed', 'url': url, 'language': language.upper(),
                                   'label': 'Zen · ' + str(server.get('server_name', 'Player')),
                                   'available': True, 'subtitles': []})
    return result

def episodes(data, anime_id):
    result = []
    seen = set()
    for episode in (data or {}).get('episodes', {}).get('episodes', []):
        try:
            number = int(episode['episode_no'])
        except (ValueError, TypeError, KeyError):
            continue
        if number < 1 or number in seen:
            continue
        seen.add(number)
        result.append({'number': number, 'title': episode.get('title'), 'playable': bool(sources(data, anime_id, number))})
    return sorted(result, key=lambda row: row['number'])

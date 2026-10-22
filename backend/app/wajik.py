"""Fixed-origin JSON adapter; never proxies video or bypasses provider access checks."""
import re
import httpx
from fastapi import APIRouter, HTTPException, Query
from .core.config import config
from .services import otakudesu

router = APIRouter(prefix='/api/wajik', tags=['Wajik'])

async def request(path: str, params=None):
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=False) as client:
            response = await client.get(config.wajik_base_url.rstrip('/') + '/otakudesu/' + path, params=params)
        if response.status_code in (401, 403):
            raise HTTPException(403, 'Wajik menolak akses ke sumber ini (403). Coba judul lain atau tunggu penyedia memperbaiki akses.')
        if response.status_code == 429:
            raise HTTPException(429, 'Batas permintaan Wajik tercapai. Coba lagi nanti.')
        response.raise_for_status()
        body = response.json()
        status = body.get('statusCode', 200)
        if status != 200 or not isinstance(body.get('data'), dict):
            raise HTTPException(403 if status in (401, 403) else 502, 'Sumber Wajik menolak akses.' if status in (401, 403) else 'Data Wajik belum tersedia.')
        return {'data': body['data'], 'pagination': body.get('pagination')}
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, TypeError):
        raise HTTPException(502, 'Tidak dapat memuat Wajik. Penyedia mungkin sedang tidak tersedia.') from None

@router.get('/search')
async def search(q: str = Query(min_length=1, max_length=150)):
    return await request('search', {'q': q})

@router.get('/{kind}/{item_id}')
async def item(kind: str, item_id: str):
    if kind not in ('anime', 'episode', 'server') or not re.fullmatch(r'[A-Za-z0-9_=-]{1,500}', item_id):
        raise HTTPException(422, 'ID sumber Wajik tidak valid.')
    try:
        return await request(kind + '/' + item_id)
    except HTTPException as original:
        if kind in ('anime', 'episode') and original.status_code in (403, 502):
            try:
                return await otakudesu.fetch(kind, item_id)
            except HTTPException:
                pass
        raise original

@router.get('/episode/{episode_id}/mirror/{server_id}')
async def direct_mirror(episode_id: str, server_id: str):
    return await otakudesu.fetch_mirror(episode_id, server_id)

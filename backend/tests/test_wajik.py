import asyncio
import httpx
import pytest
from fastapi import HTTPException
from backend.app import wajik

def mock_upstream(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setattr(wajik.httpx, 'AsyncClient', lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))

def test_search_preserves_provider_ids(monkeypatch):
    def respond(request):
        assert request.url.path == '/otakudesu/search'
        assert request.url.params['q'] == 'Frieren'
        return httpx.Response(200, json={'statusCode': 200, 'data': {'animeList': [{'animeId': 'provider-season-2', 'title': 'Season 2'}]}})
    mock_upstream(monkeypatch, respond)
    result = asyncio.run(wajik.search('Frieren'))
    assert result['data']['animeList'][0]['animeId'] == 'provider-season-2'

@pytest.mark.parametrize('http_status,body_status', [(403, 403), (200, 403), (429, 429), (500, 500)])
def test_provider_failure_is_not_reported_as_success(monkeypatch, http_status, body_status):
    calls = []
    def respond(request):
        calls.append(request)
        return httpx.Response(http_status, json={'statusCode': body_status, 'data': None})
    mock_upstream(monkeypatch, respond)
    with pytest.raises(HTTPException) as error:
        asyncio.run(wajik.item('anime', 'valid-id'))
    assert error.value.status_code == (403 if body_status == 403 else 429 if http_status == 429 else 502)
    assert len(calls) == 1

@pytest.mark.parametrize('kind,item_id', [('video', 'x'), ('anime', '..'), ('episode', 'https://example.com'), ('server', 'a/b')])
def test_untrusted_paths_are_rejected(kind, item_id):
    with pytest.raises(HTTPException) as error:
        asyncio.run(wajik.item(kind, item_id))
    assert error.value.status_code == 422

def test_full_episode_list_is_preserved(monkeypatch):
    episodes = [{'episodeId': f'episode-{n}', 'title': f'Episode {n}'} for n in range(1, 151)]
    mock_upstream(monkeypatch, lambda request: httpx.Response(200, json={'statusCode': 200, 'data': {'episodeList': episodes}}))
    assert len(asyncio.run(wajik.item('anime', 'series'))['data']['episodeList']) == 150

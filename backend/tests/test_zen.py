import asyncio
import httpx
import pytest
from backend.app.services import zen

def test_only_trusted_embeds_and_valid_episode_numbers():
    data = {'episodes': {'episodes': [
        {'episode_no': 2, 'title': 'Second', 'streams': {'sub': [{'embed': 'https://api.anizen.tr/player/abc', 'server_name': 'HD'}]}},
        {'episode_no': 1, 'streams': {'sub': [{'embed': 'javascript:alert(1)'}]}},
        {'episode_no': 'bad'}, {'episode_no': 0}, {'episode_no': 2},
    ]}}
    rows = zen.episodes(data, 101922)
    assert [r['number'] for r in rows] == [1, 2]
    assert [r['playable'] for r in rows] == [False, True]
    assert zen.sources(data, 101922, 2)[0]['provider'] == 'embed'
    assert zen.embed_url('https://api.anizen.tr.evil.com/player/x') is None
    assert zen.embed_url('https://user:pass@api.anizen.tr/player/x') is None
    assert zen.embed_url('https://api.anizen.tr:8080/player/x') is None

@pytest.mark.parametrize('use_mal', [False, True])
def test_matches_anilist_id_instead_of_similar_title(monkeypatch, use_mal):
    monkeypatch.setattr(zen, 'slugs', {})
    async def detail(_): return {'anime': {'title': 'Test', 'mal_id': 38000}}
    monkeypatch.setattr(zen.metadata, 'detail', detail)
    def handler(request):
        if request.url.path == '/api/search':
            data = [{'id': 'wrong-season'}, {'id': 'correct-season'}]
        else:
            correct = request.url.params['id'] == 'correct-season'
            data = {'anilistId': 22 if correct else 11}
            if use_mal:
                data = {'anilistId': None, 'malId': 38000 if correct else 999}
        return httpx.Response(200, json={'success': True, 'results': {'data': data}})
    client = httpx.AsyncClient
    monkeypatch.setattr(zen.httpx, 'AsyncClient', lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))
    result = asyncio.run(zen.lookup(22))
    assert result['malId' if use_mal else 'anilistId'] == (38000 if use_mal else 22)
    assert zen.slugs[22] == 'correct-season'

def test_alternate_title_and_later_candidate_survive_broken_result(monkeypatch):
    monkeypatch.setattr(zen, 'slugs', {})
    async def detail(_):
        return {'anime': {'title': 'English', 'titles': ['English', 'Romaji'], 'mal_id': 38000}}
    monkeypatch.setattr(zen.metadata, 'detail', detail)
    def handler(request):
        if request.url.path == '/api/search':
            data = [] if request.url.params['keyword'] == 'English' else [
                {'id': 'broken'}, {'id': 'wrong1'}, {'id': 'wrong2'}, {'id': 'correct'}]
        elif request.url.params['id'] == 'broken':
            return httpx.Response(503)
        else:
            data = {'anilistId': 22 if request.url.params['id'] == 'correct' else 11}
        return httpx.Response(200, json={'success': True, 'results': {'data': data}})
    client = httpx.AsyncClient
    monkeypatch.setattr(zen.httpx, 'AsyncClient', lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))
    assert asyncio.run(zen.lookup(22))['anilistId'] == 22
    assert zen.slugs[22] == 'correct'

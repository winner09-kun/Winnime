import asyncio
import base64
import json
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from backend.app import wajik
from backend.app.services import otakudesu

TOKEN = base64.b64encode(json.dumps({'id': 206867, 'i': 1, 'q': '480p'}).encode()).decode()
HTML = '''<div class="venutama"><h1>Episode 3</h1><div class="prevnext">
<a href="https://otakudesu.blog/anime/series/">All</a></div>
<div class="mirrorstream"><ul class="m480p"><li><a data-content="TOKEN">blogs</a></li></ul></div></div>
<script>$('.mirrorstream a').on('click',function(){
$.ajax("https://otakudesu.blog/wp-admin/admin-ajax.php",{data:{action:"aa1208d27f29ca340c92c66d1926f13f"}});
$.ajax("https://otakudesu.blog/wp-admin/admin-ajax.php",{data:{...e,nonce:a,action:"2a3505c93b0035d3f455df82bf976b84"}});});</script>'''.replace('TOKEN', TOKEN)

def mock(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setattr(otakudesu.httpx, 'AsyncClient', lambda **kw: client(transport=httpx.MockTransport(handler), **kw))

def test_fallback_episode_to_direct_mirror_through_routes(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.host != 'otakudesu.blog':
            return httpx.Response(403)
        if request.method == 'GET':
            return httpx.Response(200, text=HTML, headers={'set-cookie': 'session=test; Path=/; Secure'})
        assert request.headers['referer'] == 'https://otakudesu.blog/episode/ep-3/'
        assert request.headers['cookie'] == 'session=test'
        fields = parse_qs(request.content.decode())
        if fields['action'] == ['aa1208d27f29ca340c92c66d1926f13f']:
            assert set(fields) == {'action'}
            return httpx.Response(200, json={'data': 'fresh-nonce'})
        assert fields == {'id': ['206867'], 'i': ['1'], 'q': ['480p'], 'nonce': ['fresh-nonce'],
                          'action': ['2a3505c93b0035d3f455df82bf976b84']}
        return httpx.Response(200, json={'data': base64.b64encode(b'<script>ignored()</script><iframe src="https://player.example.com/embed/1"></iframe>').decode()})
    mock(monkeypatch, handler)
    app = FastAPI()
    app.include_router(wajik.router)
    with TestClient(app) as client:
        episode = client.get('/api/wajik/episode/ep-3')
        assert episode.status_code == 200
        server = episode.json()['data']['server']['qualityList'][0]['serverList'][0]
        assert server['provider'] == 'otakudesu'
        assert server['title'] == 'blogs'
        result = client.get('/api/wajik/episode/ep-3/mirror/' + server['serverId'])
        assert result.status_code == 200
        assert result.json()['data'] == {'url': 'https://player.example.com/embed/1'}
    assert [r.method for r in calls] == ['GET', 'GET', 'GET', 'POST', 'POST']

def test_foreign_selection_never_posts(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, text=HTML)
    mock(monkeypatch, handler)
    with pytest.raises(HTTPException) as error:
        asyncio.run(otakudesu.fetch_mirror('different-episode', 'not-a-listed-server'))
    assert error.value.status_code == 404
    assert [r.method for r in calls] == ['GET']

@pytest.mark.parametrize('reply', [None, [], {'data': False}, {'success': False, 'data': 'x'}, {'data': '!not-base64!'},
    {'data': base64.b64encode(b'<iframe src="http://localhost/private"></iframe>').decode()},
    {'data': base64.b64encode(b'<iframe src="https://127.0.0.1/private"></iframe>').decode()},
    {'data': base64.b64encode(b'<iframe src="https://a.example/a"></iframe><iframe src="https://b.example/b"></iframe>').decode()}])
def test_malformed_or_unsafe_embed_fails_closed(monkeypatch, reply):
    def handler(request):
        if request.method == 'GET':
            return httpx.Response(200, text=HTML)
        if parse_qs(request.content.decode())['action'] == ['aa1208d27f29ca340c92c66d1926f13f']:
            return httpx.Response(200, json={'data': 'nonce'})
        return httpx.Response(200, text=json.dumps(reply))
    mock(monkeypatch, handler)
    with pytest.raises(HTTPException) as error:
        asyncio.run(otakudesu.fetch_mirror('ep-3', otakudesu.mirror_id(TOKEN)))
    assert error.value.status_code == 502

def test_changed_handler_is_not_guessed(monkeypatch):
    mock(monkeypatch, lambda request: httpx.Response(200, text=HTML.replace('nonce:a,action:', 'changed:a,action:')))
    with pytest.raises(HTTPException) as error:
        asyncio.run(otakudesu.fetch_mirror('ep-3', otakudesu.mirror_id(TOKEN)))
    assert error.value.status_code == 502

def test_only_scoped_valid_choices_are_published():
    parser = otakudesu.Mirrors()
    parser.feed('<div class><a data-content>empty</a></div><a data-content="' + TOKEN + '">ad</a>' + HTML + '<div class="mirrorstream"><a data-content="invalid">bad</a></div>')
    assert len(parser.choices) == 1
    assert parser.servers()['qualityList'][0]['title'] == '480p'

@pytest.mark.parametrize('status', [403, 429, 500])
def test_upstream_refusal_is_reported(monkeypatch, status):
    mock(monkeypatch, lambda request: httpx.Response(status))
    with pytest.raises(HTTPException) as error:
        asyncio.run(otakudesu.fetch_mirror('ep-3', otakudesu.mirror_id(TOKEN)))
    assert error.value.status_code == 502

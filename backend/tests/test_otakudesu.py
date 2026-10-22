import asyncio
import httpx
import pytest
from fastapi import HTTPException
from backend.app.services import otakudesu

def test_parser_ignores_ads_related_titles_and_untrusted_links():
    page = otakudesu.Page()
    page.feed('''<h1>Advertisement</h1><div class="venser"><h1>Correct title</h1>
    <div class="episodelist"><a href="https://otakudesu.blog/episode/ep-1/">Episode 1</a>
    <a href="https://evil.test/episode/ep-2/">Wrong</a></div>
    <a href="https://otakudesu.blog/episode/related/">Related</a></div>''')
    assert ''.join(page.title_parts) == 'Correct title'
    assert list(page.items) == ['ep-1']

def test_episode_navigation_and_trusted_player(monkeypatch):
    html = '''<div class="venutama"><h1>Episode 2</h1><div class="prevnext">
    <select id="selectcog"><option value="https://otakudesu.blog/episode/ep-3/">3</option>
    <option value="https://otakudesu.blog/episode/ep-2/">2</option>
    <option value="https://otakudesu.blog/episode/ep-1/">1</option></select>
    <a href="https://otakudesu.blog/anime/series/">All</a></div>
    <div id="pembed"><iframe src="https://desustream.net/dstream/test"></iframe></div></div>'''
    client = httpx.AsyncClient
    monkeypatch.setattr(otakudesu.httpx, 'AsyncClient', lambda **kwargs: client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=html)), **kwargs))
    data = asyncio.run(otakudesu.fetch('episode', 'ep-2'))['data']
    assert data['nextEpisode']['episodeId'] == 'ep-3'
    assert data['prevEpisode']['episodeId'] == 'ep-1'
    assert data['animeId'] == 'series'
    assert data['defaultStreamingUrl'] == 'https://desustream.net/dstream/test'
    page = otakudesu.Page()
    page.feed('<div id="pembed"><iframe src="https://evil.test/video"></iframe></div>')
    assert page.stream is None

def test_invalid_source_id_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(otakudesu.fetch('anime', '../private'))
    assert exc.value.status_code == 422

def test_resolves_published_blogger_frame_only(monkeypatch):
    calls = []
    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, text='<iframe src="https://www.blogger.com/video.g?token=example"></iframe>')
    client = httpx.AsyncClient
    monkeypatch.setattr(otakudesu.httpx, 'AsyncClient', lambda **kwargs: client(transport=httpx.MockTransport(respond), **kwargs))
    assert asyncio.run(otakudesu.resolve_player('https://desustream.net/dstream/test')) == 'https://www.blogger.com/video.g?token=example'
    assert asyncio.run(otakudesu.resolve_player('http://127.0.0.1/private')) == 'http://127.0.0.1/private'
    assert len(calls) == 1
    for url in ['https://www.blogger.com.evil.test/video.g?token=x', 'javascript:alert(1)', 'https://www.blogger.com/video.g?token=']:
        frame = otakudesu.BloggerFrame()
        frame.feed(f'<iframe src="{url}"></iframe>')
        assert frame.url is None

def test_player_resolution_keeps_original_on_failure(monkeypatch):
    client = httpx.AsyncClient
    monkeypatch.setattr(otakudesu.httpx, 'AsyncClient', lambda **kwargs: client(transport=httpx.MockTransport(lambda r: httpx.Response(403)), **kwargs))
    url = 'https://desustream.net/dstream/test'
    assert asyncio.run(otakudesu.resolve_player(url)) == url

import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.services.metadata import normalize

ANIME={'id':1,'title':'Test fixture','titles':[],'description':'','genres':[],'studios':[],'links':[],'characters':[],'relations':[],'recommendations':[]}

@pytest.fixture
def client(monkeypatch):
    from backend.app.services import zen
    async def no_zen(_): return None
    monkeypatch.setattr(zen, 'lookup', no_zen)
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions=sessionmaker(engine)
    def database():
        with sessions() as db: yield db
    app.dependency_overrides[get_db]=database
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()
    engine.dispose()

def test_watchlist_lifecycle(client):
    assert client.get('/api/watchlist').json()==[]
    result=client.post('/api/watchlist',json={'anime_id':1,'anime':ANIME})
    assert result.status_code==201
    assert client.patch('/api/watchlist/1',json={'status':'WATCHING'}).json()['status']=='WATCHING'
    assert client.get('/api/watchlist').json()[0]['anime']['title']=='Test fixture'
    assert client.delete('/api/watchlist/1').status_code==204
    assert client.get('/api/watchlist').json()==[]

def test_history_upsert_resume_and_reset(client):
    body={'anime_id':1,'episode':2,'position':123,'duration':1400,'anime':ANIME}
    assert client.post('/api/history',json=body).status_code==200
    client.post('/api/history',json={**body,'position':240})
    history=client.get('/api/history').json()
    assert len(history)==1 and history[0]['position']==240 and history[0]['episode_id']=='1:2'
    assert client.delete('/api/history/1:2').status_code==204
    assert client.get('/api/history').json()==[]

def test_invalid_data_does_not_persist(client):
    assert client.post('/api/watchlist',json={'anime_id':2,'anime':ANIME}).status_code==422
    assert client.post('/api/history',json={'anime_id':1,'episode':0,'position':-1,'duration':0,'anime':ANIME}).status_code==422
    assert client.patch('/api/watchlist/999',json={'status':'COMPLETED'}).status_code==404

def test_sources_require_authorization_and_valid_url(client):
    source={'anime_id':1,'episode':1,'provider':'youtube','url':'abcdefghijk','authorized':True}
    assert client.post('/api/sources',json={**source,'authorized':False}).status_code==422
    assert client.post('/api/sources',json={**source,'url':'invalid'}).status_code==422
    assert client.post('/api/sources',json={**source,'provider':'mp4','url':'javascript:alert(1)'}).status_code==422
    created=client.post('/api/sources',json=source)
    assert created.status_code==201
    assert len(client.get('/api/episodes/1:1/sources').json())==1
    assert client.get('/api/episodes/1:2/sources').json()==[]
    assert client.get('/api/episodes/invalid/sources').status_code==422
    client.delete('/api/sources/'+str(created.json()['id']))
    assert client.get('/api/episodes/1:1/sources').json()==[]

def test_settings_patch_preserves_other_values(client):
    client.patch('/api/settings',json={'auto_next':True})
    client.patch('/api/settings',json={'autoplay':True})
    settings=client.get('/api/settings').json()
    assert settings['autoplay'] and settings['auto_next'] and settings['show_completed']

def test_normalizer_keeps_provider_ids_distinct():
    anime=normalize({'id':100,'idMal':200,'title':{'romaji':'Romaji','english':None,'native':'日本語'},'description':'<b>A</b> &amp; B','averageScore':85})
    assert anime.id==100 and anime.mal_id==200
    assert anime.title=='Romaji' and anime.score==8.5 and anime.description=='A & B'
    assert anime.episodes is None

def test_episode_metadata_uses_verified_mal_id(client,monkeypatch):
    from backend.app.services import metadata
    async def detail(_): return {'anime':{**ANIME,'mal_id':200}}
    called=[]
    async def request(url):
        called.append(url)
        return {'data':[{'mal_id':1,'title':'Real episode title','aired':None}], 'pagination':{'has_next_page':False}}
    async def uncached(key,fetch, **kwargs): return await fetch()
    monkeypatch.setattr(metadata,'detail',detail)
    monkeypatch.setattr(metadata,'request',request)
    monkeypatch.setattr(metadata,'cached',uncached)
    result=client.get('/api/anime/100/episodes').json()
    assert called==['https://api.jikan.moe/v4/anime/200/episodes?page=1']
    assert result['items'][0]['playable'] is False

def test_cache_returns_stale_on_provider_failure(monkeypatch):
    from backend.app.services import metadata
    engine=create_engine('sqlite://',poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(metadata,'Session',sessionmaker(engine))
    monkeypatch.setattr(metadata.config,'cache_ttl',-1)
    async def fresh(): return {'items':[{'id':123}]}
    async def failed(): raise RuntimeError('Provider offline')
    async def run():
        await metadata.cached('fixture',fresh)
        result=await metadata.cached('fixture',failed)
        assert result['stale'] and result['items'][0]['id']==123
    asyncio.run(run())
    engine.dispose()

def test_configured_video_remains_playable_when_episode_provider_fails(client,monkeypatch):
    from fastapi import HTTPException
    from backend.app.services import metadata
    async def unavailable(*args): raise HTTPException(503, 'Provider offline')
    monkeypatch.setattr(metadata,'episodes',unavailable)
    client.post('/api/sources',json={'anime_id':1,'episode':1,'provider':'youtube','url':'abcdefghijk','authorized':True})
    result=client.get('/api/anime/1/episodes')
    assert result.status_code==200
    assert result.json()['items']==[{'number':1,'title':None,'playable':True,'configured':True}]
    assert client.get('/api/anime/2/episodes').status_code==503

def test_slow_provider_returns_stale_cache_within_deadline(monkeypatch):
    from backend.app.services import metadata
    engine = create_engine('sqlite://', poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(metadata, 'Session', sessionmaker(engine))
    monkeypatch.setattr(metadata.config, 'cache_ttl', -1)
    async def fresh(): return {'items': [{'number': 1}]}
    async def slow(): await asyncio.sleep(60)
    async def run():
        await metadata.cached('slow-episodes', fresh)
        result = await asyncio.wait_for(
            metadata.cached('slow-episodes', slow, fetch_timeout=0.01), timeout=1)
        assert result['stale'] is True
        assert result['items'] == [{'number': 1}]
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await metadata.cached('uncached-episodes', slow, fetch_timeout=0.01)
        assert exc.value.status_code == 503
    asyncio.run(run())
    engine.dispose()

def test_provider_list_preserves_extra_configured_episodes(client, monkeypatch):
    from backend.app.services import zen
    async def lookup(_):
        return {'episodes': {'episodes': [{'episode_no': 1, 'streams': {}}]}}
    monkeypatch.setattr(zen, 'lookup', lookup)
    client.post('/api/sources', json={'anime_id': 1, 'episode': 2, 'provider': 'youtube', 'url': 'abcdefghijk', 'authorized': True})
    items = client.get('/api/anime/1/episodes').json()['items']
    assert [item['number'] for item in items] == [1, 2]
    assert items[1]['playable'] is True
    assert client.get('/api/episodes/1:0/sources').status_code == 422

"""Read public episode pages when the hosted Wajik API is unavailable."""
from html.parser import HTMLParser
from urllib.parse import urlsplit
import base64
import binascii
import ipaddress
import json
import re
import httpx
from fastapi import HTTPException

BASE = 'https://otakudesu.blog'

def mirror_id(token):
    return base64.urlsafe_b64encode(token.encode()).decode().rstrip('=')

def mirror_payload(value):
    try:
        if not isinstance(value, str) or len(value) > 512:
            return None
        data = json.loads(base64.b64decode(value, validate=True))
        if (isinstance(data, dict) and set(data) == {'id', 'i', 'q'}
                and type(data['id']) is int and data['id'] > 0
                and type(data['i']) is int and data['i'] >= 0
                and isinstance(data['q'], str) and re.fullmatch(r'[0-9]{3,4}p', data['q'])):
            return data
    except (ValueError, UnicodeError, binascii.Error):
        pass
    return None

class Mirrors(HTMLParser):
    """Read published mirror choices and the known inline AJAX handler shape."""
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.link = None
        self.choices = {}
        self.script = None
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            if self.depth:
                self.depth += 1
            elif 'mirrorstream' in (attrs.get('class') or '').split():
                self.depth = 1
        if tag == 'a' and self.depth:
            token = attrs.get('data-content', '')
            payload = mirror_payload(token)
            if payload:
                self.link = (token, payload, [])
        if tag == 'script' and not attrs.get('src'):
            self.script = []

    def handle_data(self, text):
        if self.link:
            self.link[2].append(text)
        if self.script is not None:
            self.script.append(text)

    def handle_endtag(self, tag):
        if tag == 'div' and self.depth:
            self.depth -= 1
        if tag == 'a' and self.link:
            token, payload, parts = self.link
            self.choices[token] = {'payload': payload, 'title': ''.join(parts).strip()}
            self.link = None
        if tag == 'script' and self.script is not None:
            self.scripts.append(''.join(self.script))
            self.script = None

    def actions(self):
        # Accept only the observed handler shape; never execute source JavaScript.
        handlers = [s for s in self.scripts if BASE + '/wp-admin/admin-ajax.php' in s and 'mirrorstream' in s]
        nonces, embeds = set(), set()
        for script in handlers:
            nonces.update(re.findall(r'data\s*:\s*\{\s*action\s*:\s*[\"\x27]([a-f0-9]{32})[\"\x27]\s*\}', script))
            embeds.update(re.findall(r'nonce\s*:\s*[\w.$]+\s*,\s*action\s*:\s*[\"\x27]([a-f0-9]{32})[\"\x27]', script))
        if len(nonces) != 1 or len(embeds) != 1:
            raise ValueError('Unrecognized mirror handler')
        return next(iter(nonces)), next(iter(embeds))

    def servers(self):
        groups = {}
        for token, choice in self.choices.items():
            quality = choice['payload']['q']
            groups.setdefault(quality, []).append({
                'title': choice['title'] or quality,
                'serverId': mirror_id(token),
                'provider': 'otakudesu',
            })
        return {'qualityList': [{'title': q, 'serverList': servers} for q, servers in groups.items()]}

class MirrorEmbed(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag != 'iframe':
            return
        value = dict(attrs).get('src', '')
        try:
            url = urlsplit(value)
            host = url.hostname or ''
            if (url.scheme != 'https' or url.username or url.password or url.port not in (None, 443)
                    or '.' not in host or host.endswith(('.localhost', '.local', '.internal'))):
                return
            try:
                ipaddress.ip_address(host)
                return
            except ValueError:
                pass
            self.urls.append(value)
        except ValueError:
            pass

async def fetch_mirror(episode_id, server_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', episode_id) or not re.fullmatch(r'[A-Za-z0-9_-]{1,700}', server_id):
        raise HTTPException(422, 'ID mirror tidak valid.')
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            source = f'{BASE}/episode/{episode_id}/'
            page = await client.get(source)
            page.raise_for_status()
            mirrors = Mirrors()
            mirrors.feed(page.text)
            # Rebind the selection to the current episode; never accept caller POST fields.
            choices = {mirror_id(token): token for token in mirrors.choices}
            token = choices.get(server_id)
            if token is None:
                raise HTTPException(404, 'Mirror tidak tersedia pada episode ini. Muat ulang daftar server.')
            nonce_action, embed_action = mirrors.actions()
            headers = {'Referer': source, 'Origin': BASE}
            nonce_response = await client.post(BASE + '/wp-admin/admin-ajax.php', data={'action': nonce_action}, headers=headers)
            nonce_response.raise_for_status()
            body = nonce_response.json()
            nonce = body.get('data') if isinstance(body, dict) and body.get('success') is not False else None
            if not isinstance(nonce, str) or not nonce:
                raise ValueError('Invalid nonce response')
            response = await client.post(BASE + '/wp-admin/admin-ajax.php', data={
                **mirrors.choices[token]['payload'], 'nonce': nonce, 'action': embed_action,
            }, headers=headers)
            response.raise_for_status()
            body = response.json()
            encoded = body.get('data') if isinstance(body, dict) and body.get('success') is not False else None
            if not isinstance(encoded, str):
                raise ValueError('Invalid embed response')
            embed = MirrorEmbed()
            embed.feed(base64.b64decode(encoded, validate=True).decode('utf-8'))
            if len(embed.urls) != 1:
                raise ValueError('Missing or ambiguous HTTPS iframe')
        return {'data': {'url': await resolve_player(embed.urls[0])}, 'provider': 'Otakudesu'}
    except (httpx.HTTPError, ValueError, UnicodeError, binascii.Error):
        raise HTTPException(502, 'Mirror Otakudesu belum dapat dimuat. Coba server lain atau muat ulang episode.') from None

class BloggerFrame(HTMLParser):
    """Recognize only the public Blogger embed published by the source player."""
    def __init__(self):
        super().__init__()
        self.url = None

    def handle_starttag(self, tag, attrs):
        if tag != 'iframe':
            return
        value = dict(attrs).get('src', '')
        try:
            url = urlsplit(value)
            if (url.scheme == 'https' and url.netloc == 'www.blogger.com'
                    and url.path == '/video.g' and url.query.startswith('token=')
                    and len(url.query) > 6):
                self.url = value
        except ValueError:
            pass

async def resolve_player(url):
    if not url:
        return url
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc not in ('desustream.net', 'desustream.com'):
        return url
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.get(url)
            response.raise_for_status()
        frame = BloggerFrame()
        frame.feed(response.text)
        return frame.url or url
    except httpx.HTTPError:
        return url

def page_id(value, kind):
    try:
        url = urlsplit(value or '')
        if url.scheme != 'https' or url.netloc != 'otakudesu.blog':
            return None
        match = re.fullmatch(r'/' + kind + r'/([A-Za-z0-9_-]+)/?', url.path)
        return match[1] if match else None
    except ValueError:
        return None

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.divs = []
        self.title_parts = []
        self.in_title = False
        self.in_select = False
        self.link = None
        self.items = {}
        self.anime_id = None
        self.stream = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'div':
            self.divs.append(set((a.get('class') or '').split()) | {a.get('id')})
        scopes = set().union(*self.divs) if self.divs else set()
        if tag == 'h1' and ('venser' in scopes or 'venutama' in scopes):
            self.in_title = True
        if tag == 'select' and a.get('id') == 'selectcog':
            self.in_select = True
        if tag == 'a' and 'prevnext' in scopes:
            self.anime_id = page_id(a.get('href'), 'anime') or self.anime_id
        if (tag == 'a' and 'episodelist' in scopes) or (tag == 'option' and self.in_select):
            ident = page_id(a.get('href') if tag == 'a' else a.get('value'), 'episode')
            if ident:
                self.link = (tag, ident, [])
        if tag == 'iframe' and 'pembed' in scopes:
            value = a.get('src', '')
            try:
                url = urlsplit(value)
                if url.scheme == 'https' and url.hostname in ('desustream.net', 'desustream.com') and not url.username and not url.password and url.port in (None, 443):
                    self.stream = value
            except ValueError:
                pass

    def handle_data(self, value):
        if self.in_title:
            self.title_parts.append(value)
        if self.link:
            self.link[2].append(value)

    def handle_endtag(self, tag):
        if tag == 'div' and self.divs:
            self.divs.pop()
        if tag == 'h1':
            self.in_title = False
        if tag == 'select':
            self.in_select = False
        if self.link and tag == self.link[0]:
            _, ident, parts = self.link
            self.items[ident] = {'episodeId': ident, 'title': ''.join(parts).strip()}
            self.link = None

async def fetch(kind, ident):
    if kind not in ('anime', 'episode') or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', ident):
        raise HTTPException(422, 'ID halaman sumber tidak valid.')
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.get(f'{BASE}/{kind}/{ident}/')
            response.raise_for_status()
        page = Page()
        page.feed(response.text)
        title = ''.join(page.title_parts).strip()
        items = list(page.items.values())
        if not title or (kind == 'anime' and not items) or (kind == 'episode' and not page.anime_id):
            raise ValueError('Incomplete public page')
        data = {'title': title, 'sourceUrl': f'{BASE}/{kind}/{ident}/'}
        if kind == 'anime':
            data['episodeList'] = items
        else:
            data.update(animeId=page.anime_id, defaultStreamingUrl=await resolve_player(page.stream), info={'episodeList': items})
            mirrors = Mirrors()
            mirrors.feed(response.text)
            data['server'] = mirrors.servers()
            # The source selector lists newest episodes first.
            ids = list(page.items)
            if ident in ids:
                index = ids.index(ident)
                if index > 0:
                    data['nextEpisode'] = items[index - 1]
                if index + 1 < len(items):
                    data['prevEpisode'] = items[index + 1]
        return {'data': data, 'pagination': None, 'provider': 'Otakudesu',
                'note': 'API Wajik tidak tersedia. Data dimuat dari halaman publik Otakudesu.'}
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, 'Halaman sumber Otakudesu belum dapat dimuat.') from None

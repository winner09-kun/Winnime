<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api, errorMessage } from '../services/api';
import LoadState from '../components/LoadState.vue';
import EpisodeFilter from '../components/EpisodeFilter.vue';
type EpisodeLink = { title: string; episodeId: string };
type AnimeCard = { title: string; animeId: string; poster?: string; status?: string };
type Detail = { title: string; poster?: string; synopsis?: { paragraphList: string[] }; episodeList?: EpisodeLink[] };
type Episode = { title: string; animeId: string; sourceUrl?: string; defaultStreamingUrl?: string; prevEpisode?: EpisodeLink; nextEpisode?: EpisodeLink; info?: { episodeList: EpisodeLink[] }; server?: { qualityList: { title: string; serverList: { title: string; serverId: string; provider?: 'otakudesu' }[] }[] } };
const route = useRoute(), router = useRouter();
const term = ref(String(route.query.q || '')), loading = ref(false), error = ref('');
const providerNote = ref('');
const results = ref<AnimeCard[]>([]), detail = ref<Detail>(), episode = ref<Episode>();
const stream = ref(''), serverError = ref(''), serverLoading = ref(false), selectedServer = ref('');
const controller = new AbortController();
let serverRequest = 0;
function safeEmbed(value?: string) {
  try {
    const url = new URL(value || '');
    const host = url.hostname.toLowerCase();
    if (url.protocol !== 'https:' || url.username || url.password || url.port || !host.includes('.') || /(^[\d.]+$|[:\[\]]|(^|\.)localhost$|\.local$|\.internal$)/.test(host)) return '';
    return url.href;
  } catch { return ''; }
}
async function load() {
  loading.value = true;
  error.value = '';
  providerNote.value = '';
  ++serverRequest;
  selectedServer.value = '';
  serverError.value = '';
  serverLoading.value = false;
  stream.value = '';
  try {
    if (route.params.episodeId) {
      const response = await api.get('/wajik/episode/' + encodeURIComponent(String(route.params.episodeId)), { signal: controller.signal });
      episode.value = response.data.data;
      providerNote.value = response.data.note || '';
      stream.value = safeEmbed(episode.value?.defaultStreamingUrl);
      if (!stream.value) serverError.value = 'Sumber utama tidak tersedia. Pilih server lain jika ada.';
    } else if (route.params.animeId) {
      const response = await api.get('/wajik/anime/' + encodeURIComponent(String(route.params.animeId)), { signal: controller.signal });
      detail.value = response.data.data;
      providerNote.value = response.data.note || '';
    } else if (term.value.trim()) {
      results.value = (await api.get('/wajik/search', { params: { q: term.value.trim() }, signal: controller.signal })).data.data.animeList || [];
    }
  } catch (e) { if (!controller.signal.aborted) error.value = errorMessage(e); }
  finally { loading.value = false; }
}
function search() {
  const q = term.value.trim();
  if (!q) return;
  if (route.query.q === q && !route.params.animeId && !route.params.episodeId) void load();
  else router.push({ path: '/streaming', query: { q } });
}
async function changeServer() {
  const ticket = ++serverRequest;
  stream.value = '';
  serverError.value = '';
  serverLoading.value = true;
  try {
    const server = episode.value?.server?.qualityList.flatMap(q => q.serverList)
      .find(s => s.serverId === selectedServer.value);
    const endpoint = server?.provider === 'otakudesu'
      ? '/wajik/episode/' + encodeURIComponent(String(route.params.episodeId)) + '/mirror/' + encodeURIComponent(selectedServer.value)
      : '/wajik/server/' + encodeURIComponent(selectedServer.value);
    const value = selectedServer.value
      ? (await api.get(endpoint, { signal: controller.signal })).data.data.url
      : episode.value?.defaultStreamingUrl;
    if (ticket !== serverRequest) return;
    stream.value = safeEmbed(value);
    if (!stream.value) serverError.value = 'Server belum memberikan alamat player HTTPS yang valid.';
  } catch (e) { if (ticket === serverRequest && !controller.signal.aborted) serverError.value = errorMessage(e); }
  finally { if (ticket === serverRequest) serverLoading.value = false; }
}
onMounted(load);
onBeforeUnmount(() => controller.abort());
</script>

<template>
  <div class="container page streaming-page">
    <div class="eyebrow">Wajik · Otakudesu</div>
    <h1>Nonton anime</h1>
    <p class="muted">Cari judul, pilih season, lalu pilih episode dari sumber Wajik.</p>
    <form class="stream-search" @submit.prevent="search">
      <input v-model="term" aria-label="Cari anime di Wajik" placeholder="Cari anime, misalnya Frieren" maxlength="150" required />
      <button class="button" :disabled="loading">Cari</button>
    </form>
    <LoadState :loading="loading" :error="error" @retry="load" />
    <p v-if="!loading && !error && providerNote" class="notice" role="status">{{ providerNote }}</p>
    <RouterLink v-if="!loading && error" :to="{ path: '/streaming', query: { q: term } }" class="button secondary">Kembali ke pencarian</RouterLink>
    <template v-if="!loading && !error">
      <section v-if="episode">
        <RouterLink :to="'/streaming/anime/' + episode.animeId" class="back-link">← Daftar episode</RouterLink>
        <h2>{{ episode.title }}</h2>
        <p class="muted">Player pihak ketiga. Progres otomatis dan pindah episode otomatis belum tersedia.</p>
        <label v-if="episode.server?.qualityList?.length" class="stream-server">Server
          <select v-model="selectedServer" @change="changeServer">
            <option value="">Server utama</option>
            <optgroup v-for="quality in episode.server.qualityList" :key="quality.title" :label="quality.title">
              <option v-for="server in quality.serverList" :key="server.serverId" :value="server.serverId">{{ server.title }}</option>
            </optgroup>
          </select>
        </label>
        <p v-if="serverLoading" role="status">Memuat server…</p>
        <p v-if="serverError" class="notice" role="alert">{{ serverError }}</p>
        <div v-if="stream" class="video-frame">
          <iframe :key="stream" :src="stream" :title="episode.title" sandbox="allow-scripts allow-same-origin allow-presentation" allow="autoplay; fullscreen; picture-in-picture; encrypted-media" allowfullscreen></iframe>
        </div>
        <p v-if="stream" class="muted">Jika player menolak koneksi, pilih server lain jika tersedia atau buka halaman sumber untuk memilih mirror.</p>
        <a v-if="safeEmbed(episode.sourceUrl)" :href="safeEmbed(episode.sourceUrl)" target="_blank" rel="noopener noreferrer" class="button secondary">Buka episode di sumber · Pilih mirror</a>
        <div class="watch-toolbar">
          <RouterLink v-if="episode.prevEpisode" :to="'/streaming/episode/' + episode.prevEpisode.episodeId" class="button secondary">← Sebelumnya</RouterLink>
          <RouterLink v-if="episode.nextEpisode" :to="'/streaming/episode/' + episode.nextEpisode.episodeId" class="button">Berikutnya →</RouterLink>
        </div>
        <EpisodeFilter v-slot="{ items }" :items="episode.info?.episodeList || []">
          <div class="episode-list">
            <RouterLink v-for="e in items" :key="e.episodeId" :to="'/streaming/episode/' + e.episodeId" class="episode-row" :aria-current="e.episodeId === route.params.episodeId ? 'page' : undefined">{{ e.title }}</RouterLink>
          </div>
        </EpisodeFilter>
      </section>
      <section v-else-if="detail">
        <RouterLink :to="{ path: '/streaming', query: { q: term } }" class="back-link">← Pencarian Wajik</RouterLink>
        <h2>{{ detail.title }}</h2>
        <p v-for="(paragraph, i) in detail.synopsis?.paragraphList || []" :key="i">{{ paragraph }}</p>
        <div class="section-heading"><h2>Daftar episode</h2><span>{{ detail.episodeList?.length || 0 }} episode</span></div>
        <p v-if="!detail.episodeList?.length" class="notice">Penyedia belum mengembalikan daftar episode untuk judul ini.</p>
        <EpisodeFilter v-slot="{ items }" :items="detail.episodeList || []">
          <div class="episode-list">
            <RouterLink v-for="e in items" :key="e.episodeId" :to="'/streaming/episode/' + e.episodeId" class="episode-row">{{ e.title }} <span class="text-link">Tonton →</span></RouterLink>
          </div>
        </EpisodeFilter>
      </section>
      <template v-else>
        <p v-if="term && !results.length" class="notice">Tidak ada hasil. Coba judul Jepang atau kata pencarian lain.</p>
        <div class="anime-grid">
          <RouterLink v-for="anime in results" :key="anime.animeId" :to="{ path: '/streaming/anime/' + anime.animeId, query: { q: term } }" class="stream-card">
            <img v-if="safeEmbed(anime.poster)" :src="safeEmbed(anime.poster)" :alt="anime.title" loading="lazy" />
            <h3>{{ anime.title }}</h3><p class="muted">{{ anime.status }}</p>
          </RouterLink>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.streaming-page h1 { margin: 12px 0; }
.stream-search { display: flex; gap: 12px; margin: 24px 0 32px; }
.stream-search input { flex: 1; min-width: 0; }
.stream-card img { width: 100%; aspect-ratio: 2/3; object-fit: cover; border-radius: 8px; }
.stream-card h3 { font-size: 15px; margin-top: 12px; }
.stream-card:hover h3 { color: var(--accent); }
.stream-server { display: flex; gap: 12px; align-items: center; margin: 20px 0; }
.stream-server select { max-width: 80%; }
.episode-row { display: flex; justify-content: space-between; gap: 16px; }
.episode-row[aria-current] { color: var(--accent); }
</style>

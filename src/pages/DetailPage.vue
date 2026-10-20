<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import {
  Star,
  Bookmark,
  Check,
  Play,
  ExternalLink,
  ArrowLeft,
  LockKeyhole,
  CalendarClock,
} from "lucide-vue-next";
import { api, errorMessage } from "../services/api";
import { useLibrary, statuses } from "../stores/library";
import type { Anime, Episode, Source, WatchStatus } from "../types";
import AnimeSection from "../components/AnimeSection.vue";
import LoadState from "../components/LoadState.vue";
const route = useRoute(),
  library = useLibrary(),
  anime = ref<Anime>(),
  episodes = ref<Episode[]>([]),
  sources = ref<Source[]>([]),
  loading = ref(true),
  error = ref(""),
  episodeError = ref(""),
  episodeLoading = ref(false),
  episodePage = ref(1),
  hasNext = ref(false),
  expanded = ref(false);
async function load() {
  loading.value = true;
  error.value = "";
  try {
    anime.value = (await api.get("/anime/" + route.params.id)).data.anime;
    sources.value = (await api.get<Source[]>("/sources")).data.filter(
      (s) => s.anime_id === Number(route.params.id) && s.available,
    );
    void loadEpisodes();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
async function loadEpisodes(more = false) {
  episodeLoading.value = true;
  episodeError.value = "";
  try {
    const page = more ? episodePage.value + 1 : 1;
    const { data } = await api.get("/anime/" + route.params.id + "/episodes", {
      params: { page },
    });
    episodes.value = more
      ? [
          ...episodes.value,
          ...data.items.filter(
            (e: Episode) => !episodes.value.some((x) => x.number === e.number),
          ),
        ]
      : data.items;
    episodePage.value = page;
    hasNext.value = data.has_next;
  } catch (e) {
    episodeError.value = errorMessage(e);
    if (!more)
      episodes.value = sources.value
        .map((s) => ({ number: s.episode, playable: true, configured: true }))
        .filter((s, i, a) => a.findIndex((x) => x.number === s.number) === i);
  } finally {
    episodeLoading.value = false;
  }
}
function watched(number: number) {
  return library.history.some(
    (h) =>
      h.anime_id === anime.value?.id && h.episode === number && h.completed,
  );
}
function upcoming(e: Episode) {
  return e.aired && Date.parse(e.aired) > Date.now();
}
async function mark(number: number) {
  if (anime.value)
    try {
      await library.progress(anime.value, number, 0, 0, true);
      library.notify("Episode ditandai selesai");
    } catch (e) {
      library.notify(errorMessage(e));
    }
}
onMounted(load);
</script>
<template>
  <div v-if="loading || error" class="container page">
    <LoadState :loading="loading" :error="error" @retry="load" />
  </div>
  <template v-else-if="anime"
    ><div
      class="detail-banner"
      :style="{
        backgroundImage: `linear-gradient(0deg,#0d0f12,transparent),url('${anime.banner || anime.cover}')`,
      }"
    ></div>
    <div class="container detail-content">
      <RouterLink to="/anime" class="back-link"
        ><ArrowLeft :size="16" />Jelajahi anime</RouterLink
      >
      <div class="detail-intro">
        <img class="detail-poster" :src="anime.cover" :alt="anime.title" />
        <div class="detail-summary">
          <div class="eyebrow">
            {{ anime.format?.replaceAll("_", " ") }}
            <span v-if="anime.year">/ {{ anime.year }}</span>
          </div>
          <h1>{{ anime.title }}</h1>
          <p class="alternative-title">
            {{ anime.titles.filter((t) => t !== anime?.title).join(" · ") }}
          </p>
          <div class="hero-meta">
            <span v-if="anime.score" class="rating"
              ><Star :size="15" fill="currentColor" />{{
                anime.score.toFixed(1)
              }}
              <small>AniList</small></span
            ><span>{{
              anime.episodes
                ? anime.episodes + " episode"
                : "Episode belum diketahui"
            }}</span
            ><span v-if="anime.duration">{{ anime.duration }} menit</span
            ><span>{{ anime.status?.replaceAll("_", " ") }}</span>
          </div>
          <div class="hero-genres">
            <RouterLink
              v-for="g in anime.genres"
              :key="g"
              :to="{ path: '/anime', query: { genre: g } }"
              >{{ g }}</RouterLink
            >
          </div>
          <div class="hero-buttons">
            <RouterLink class="button secondary" :to="{ path: '/streaming', query: { q: anime.titles.find(t => /^[\x00-\x7F]+$/.test(t)) || anime.title } }">Cari episode di Wajik</RouterLink>
            <RouterLink
              v-if="episodes.some(e => e.playable) || sources.length"
              class="button"
              :to="`/watch/${anime.id}/${Math.min(...episodes.filter(e => e.playable).map(e => e.number), ...sources.map((s) => s.episode))}`"
              ><Play :size="18" fill="currentColor" />Tonton anime</RouterLink
            ><button
              class="button"
              :class="{ secondary: library.has(anime.id) }"
              @click="
                library.has(anime.id)
                  ? library.remove(anime.id)
                  : library.save(anime)
              "
            >
              <Check v-if="library.has(anime.id)" :size="18" /><Bookmark
                v-else
                :size="18"
              />{{
                library.has(anime.id) ? "Di watchlist" : "Tambah watchlist"
              }}</button
            ><button
              class="button secondary"
              @click="library.save(anime, 'COMPLETED')"
            >
              <Check :size="18" />Tandai selesai</button
            ><select
              v-if="library.has(anime.id)"
              aria-label="Status watchlist"
              :value="
                library.watchlist.find((w) => w.anime_id === anime?.id)?.status
              "
              @change="
                library.save(
                  anime,
                  ($event.target as HTMLSelectElement).value as WatchStatus,
                )
              "
            >
              <option v-for="(label, key) in statuses" :key="key" :value="key">
                {{ label }}
              </option>
            </select>
          </div>
        </div>
      </div>
      <div class="detail-body">
        <section>
          <h2>Tentang anime</h2>
          <p class="synopsis" :class="{ expanded }">
            {{ anime.description || "Sinopsis belum tersedia." }}
          </p>
          <button
            v-if="anime.description.length > 500"
            class="text-link"
            @click="expanded = !expanded"
          >
            {{ expanded ? "Ringkas sinopsis" : "Baca selengkapnya" }}
          </button>
        </section>
        <aside class="facts">
          <div>
            <span>Studio</span
            ><strong>{{
              anime.studios.join(", ") || "Belum diketahui"
            }}</strong>
          </div>
          <div>
            <span>Musim</span
            ><strong>{{ anime.season || "—" }} {{ anime.year }}</strong>
          </div>
          <div>
            <span>AniList ID</span><strong>{{ anime.id }}</strong>
          </div>
        </aside>
      </div>
      <section v-if="anime.links.length" class="providers">
        <span>Tersedia di penyedia resmi</span
        ><a
          v-for="l in anime.links"
          :key="l.url"
          :href="l.url"
          target="_blank"
          rel="noreferrer"
          class="button secondary small"
          >{{ l.site }}<ExternalLink :size="14"
        /></a>
      </section>
      <section class="episode-section">
        <div class="section-heading">
          <div>
            <h2>Episode</h2>
            <p>
              Episode dimuat dari penyedia video. Ketersediaan pemutaran mengikuti server.
            </p>
          </div>
          <span class="muted">{{ episodeLoading ? 'Memuat episode…' : episodes.length + ' episode ditemukan' }}</span>
        </div>
        <p v-if="episodeLoading" role="status">Sedang mencari daftar episode dan sumber video…</p>
        <p v-if="episodeError" class="notice">
          {{ episodeError }} <button @click="loadEpisodes()">Coba lagi</button>
        </p>
        <div
          v-if="!episodes.length && !episodeLoading"
          class="empty-state compact"
        >
          <LockKeyhole />
          <h3>Metadata episode belum tersedia</h3>
          <p>
            Tambahkan sumber video berizin melalui
            <RouterLink to="/settings">Pengaturan</RouterLink>.
          </p>
        </div>
        <div class="episode-list">
          <article v-for="e in episodes" :key="e.number" class="episode-row">
            <span class="episode-number">{{
              String(e.number).padStart(2, "0")
            }}</span>
            <div>
              <h3>{{ e.title || "Episode " + e.number }}</h3>
              <span v-if="upcoming(e)" class="muted"
                ><CalendarClock :size="13" />Segera hadir</span
              ><span v-else-if="e.playable" class="available"
                >Sumber video tersedia</span
              ><span v-else class="muted">Pemutaran belum tersedia</span>
            </div>
            <span v-if="watched(e.number)" class="watched-label"
              ><Check :size="15" />Selesai</span
            ><button
              v-else
              class="icon-button"
              :aria-label="'Tandai episode ' + e.number + ' selesai'"
              @click="mark(e.number)"
            >
              <Check :size="18" /></button
            ><RouterLink
              v-if="e.playable"
              :to="`/watch/${anime.id}/${e.number}`"
              class="button small"
              ><Play :size="14" />Tonton</RouterLink
            ><LockKeyhole v-else class="muted" :size="17" />
          </article>
        </div>
        <button
          v-if="hasNext"
          class="button secondary load-more"
          :disabled="episodeLoading"
          @click="loadEpisodes(true)"
        >
          {{ episodeLoading ? "Memuat…" : "Muat episode berikutnya" }}
        </button>
      </section>
      <section v-if="anime.characters.length" class="anime-section">
        <div class="section-heading"><h2>Kenali karakternya</h2></div>
        <div class="character-grid">
          <div v-for="c in anime.characters" :key="c.name" class="character">
            <img :src="c.image" :alt="c.name" loading="lazy" /><span>{{
              c.name
            }}</span>
          </div>
        </div>
      </section>
      <AnimeSection
        v-if="anime.relations.length"
        title="Dalam dunia yang sama"
        :items="anime.relations.slice(0, 6)"
      /><AnimeSection
        v-if="anime.recommendations.length"
        title="Rekomendasi komunitas"
        :items="anime.recommendations.slice(0, 6)"
      /></div
  ></template>
</template>

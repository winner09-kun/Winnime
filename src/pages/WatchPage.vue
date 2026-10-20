<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowLeft,
  ArrowRight,
  LockKeyhole,
  ExternalLink,
  Check,
} from "lucide-vue-next";
import { api, errorMessage } from "../services/api";
import { useLibrary } from "../stores/library";
import type { Anime, Source, Episode } from "../types";
import VideoPlayer from "../components/VideoPlayer.vue";
import LoadState from "../components/LoadState.vue";
const route = useRoute(),
  router = useRouter(),
  library = useLibrary(),
  anime = ref<Anime>(),
  sources = ref<Source[]>([]),
  episodes = ref<Episode[]>([]),
  selected = ref(0),
  loading = ref(true),
  error = ref(""),
  playerError = ref(""),
  episode = Number(route.params.episode),
  animeId = Number(route.params.id),
  saving = ref(false);
const resume = ref(0),
  allSources = ref<Source[]>([]),
  source = computed(() => sources.value[selected.value]),
  next = computed(() =>
    episodes.value.some((s) => s.number === episode + 1 && s.playable),
  ),
  previous = computed(() =>
    episodes.value.some((s) => s.number === episode - 1 && s.playable),
  );
async function load() {
  loading.value = true;
  error.value = "";
  playerError.value = "";
  selected.value = 0;
  failedSources.clear();
  try {
    const [a, s, all] = await Promise.all([
      api.get("/anime/" + animeId),
      api.get("/episodes/" + animeId + ":" + episode + "/sources").catch((e) => {
        playerError.value = errorMessage(e);
        return { data: [] as Source[] };
      }),
      api.get<Source[]>("/sources").catch(() => ({ data: [] as Source[] })),
    ]);
    anime.value = a.data.anime;
    sources.value = s.data;
    allSources.value = all.data.filter(
      (s) => s.anime_id === animeId && s.available,
    );
    if (!sources.value.length)
      sources.value = allSources.value.filter((s) => s.episode === episode);
    await library.load();
    resume.value =
      library.history.find((h) => h.episode_id === `${animeId}:${episode}`)
        ?.position || 0;
    episodes.value = allSources.value
      .map((s) => ({ number: s.episode, playable: true }))
      .filter((s, i, a) => a.findIndex((x) => x.number === s.number) === i)
      .sort((a, b) => a.number - b.number);
    // Playback must not wait for the optional episode metadata provider.
    loading.value = false;
    try {
      episodes.value = (
        await api.get("/anime/" + animeId + "/episodes")
      ).data.items;
    } catch {
      episodes.value = allSources.value
        .map((s) => ({ number: s.episode, playable: true }))
        .filter((s, i, a) => a.findIndex((x) => x.number === s.number) === i);
    }
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
const failedSources = new Set<number>();
watch(selected, () => { playerError.value = ""; });
function playbackError(message: string) {
  failedSources.add(selected.value);
  const alternative = sources.value.findIndex((_, index) => !failedSources.has(index));
  if (alternative >= 0) {
    selected.value = alternative;
  } else {
    playerError.value = message;
  }
}
let progressQueue = Promise.resolve(),
  finished = false;
function progress(position: number, duration: number) {
  if (!anime.value || finished) return;
  const current = anime.value;
  progressQueue = progressQueue.then(async () => {
    try {
      await library.progress(current, episode, position, duration);
    } catch (e) {
      library.notify(errorMessage(e));
    }
  });
}
async function ended() {
  finished = true;
  await progressQueue;
  if (anime.value)
    try {
      await library.progress(anime.value, episode, 0, 0, true);
    } catch (e) {
      library.notify(errorMessage(e));
    }
  if (library.settings.auto_next && next.value)
    router.push(`/watch/${animeId}/${episode + 1}`);
}
onMounted(load);
</script>
<template>
  <div class="container page">
    <LoadState :loading="loading" :error="error" @retry="load" /><template
      v-if="anime && !loading && !error"
      ><RouterLink :to="'/anime/' + animeId" class="back-link"
        ><ArrowLeft :size="16" />{{ anime.title }}</RouterLink
      >
      <div class="watch-layout">
        <section>
          <VideoPlayer
            v-if="source"
            :key="source.id"
            :source="source"
            :resume="resume"
            :autoplay="library.settings.autoplay"
            @progress="progress"
            @ended="ended"
            @error="playbackError"
          />
          <div v-else class="unavailable-player">
            <LockKeyhole :size="34" />
            <h2>Pemutaran belum tersedia</h2>
            <p>Belum ada sumber video yang dapat dimuat untuk episode ini.</p>
            <button class="button" @click="load">Coba muat ulang sumber</button>
            <RouterLink :to="{ path: '/streaming', query: { q: anime.title } }" class="button secondary">Cari di Wajik</RouterLink>
            <RouterLink to="/settings" class="button secondary"
              >Konfigurasi sumber video</RouterLink
            >
          </div>
          <p v-if="playerError" class="notice" role="alert">
            {{ playerError }}
            <button class="text-link" @click="load">Muat ulang sumber</button>
          </p>
          <p v-if="source?.provider === 'embed'" class="muted">
            Jika video tidak dimulai, coba sumber lain atau buka player langsung. Jika server menampilkan 404, pilih sumber lain.
            <a :href="source.url" target="_blank" rel="noopener noreferrer" class="button secondary small">Buka player langsung <ExternalLink :size="14" /></a>
          </p>
          <div class="watch-toolbar">
            <RouterLink
              v-if="previous"
              class="button secondary small"
              :to="`/watch/${animeId}/${episode - 1}`"
              ><ArrowLeft :size="16" />Sebelumnya</RouterLink
            ><span v-else></span
            ><label v-if="sources.length > 1"
              >Sumber<select v-model="selected" aria-label="Sumber pemutaran">
                <option v-for="(s, i) in sources" :key="s.id" :value="i">
                  {{ s.label || s.provider }} · {{ s.language }}
                </option>
              </select></label
            ><RouterLink
              v-if="next"
              class="button small"
              :to="`/watch/${animeId}/${episode + 1}`"
              >Berikutnya<ArrowRight :size="16"
            /></RouterLink>
          </div>
          <div class="watch-title">
            <div class="eyebrow">EPISODE {{ episode }}</div>
            <h1>{{ anime.title }}</h1>
            <p>{{ episodes.find((e) => e.number === episode)?.title }}</p>
            <button class="text-link" @click="ended">
              <Check :size="16" />Tandai episode selesai
            </button>
          </div>
          <div class="providers">
            <a
              v-for="link in anime.links"
              :key="link.url"
              :href="link.url"
              target="_blank"
              rel="noreferrer"
              class="button secondary small"
              >{{ link.site }}<ExternalLink :size="14"
            /></a>
          </div>
        </section>
        <aside class="watch-episodes">
          <h2>Daftar episode</h2>
          <p v-if="!episodes.length" class="muted">
            Metadata episode belum tersedia.
          </p>
          <div
            v-for="e in episodes"
            :key="e.number"
            :class="['watch-episode', { current: e.number === episode }]"
          >
            <RouterLink v-if="e.playable" :to="`/watch/${animeId}/${e.number}`"
              ><span>{{ String(e.number).padStart(2, "0") }}</span>
              <div>
                {{ e.title || "Episode " + e.number
                }}<small>{{
                  e.number === episode ? "Episode dipilih" : "Sumber terhubung"
                }}</small>
              </div></RouterLink
            >
            <div v-else>
              <span>{{ String(e.number).padStart(2, "0") }}</span>
              <div>
                {{ e.title || "Episode " + e.number
                }}<small>Belum tersedia</small>
              </div>
              <LockKeyhole :size="14" />
            </div>
          </div>
          <RouterLink :to="'/anime/' + animeId" class="text-link"
            >Semua episode <ArrowRight :size="14"
          /></RouterLink>
        </aside></div
    ></template>
  </div>
</template>

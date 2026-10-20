<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import {
  ArrowRight,
  Bookmark,
  Check,
  Star,
  ChevronLeft,
  ChevronRight,
  Play,
  Clock3,
} from "lucide-vue-next";
import { api, errorMessage } from "../services/api";
import type { Anime, Catalog, Source } from "../types";
import { useLibrary } from "../stores/library";
import AnimeSection from "../components/AnimeSection.vue";
import LoadState from "../components/LoadState.vue";
const library = useLibrary(),
  trending = ref<Anime[]>([]),
  seasonal = ref<Anime[]>([]),
  recent = ref<Anime[]>([]),
  recommended = ref<Anime[]>([]),
  loading = ref(true),
  error = ref(""),
  sectionError = ref(""),
  stale = ref(false),
  index = ref(0);
const playable = ref<{ anime: Anime; episode: number }[]>([]);
async function loadPlayable() {
  try {
    const { data } = await api.get<Source[]>("/sources");
    const available = data.filter((s) => s.available);
    const ids = [...new Set(available.map((s) => s.anime_id))];
    const results = await Promise.allSettled(
      ids.map(async (id) => ({
        anime: (await api.get("/anime/" + id)).data.anime as Anime,
        episode: Math.min(
          ...available.filter((s) => s.anime_id === id).map((s) => s.episode),
        ),
      })),
    );
    playable.value = results.flatMap((r) =>
      r.status === "fulfilled" ? [r.value] : [],
    );
  } catch (e) {
    sectionError.value = errorMessage(e);
  }
}
const featured = computed(() =>
    [
      ...playable.value.map((p) => p.anime),
      ...trending.value.filter(
        (a) => !playable.value.some((p) => p.anime.id === a.id),
      ),
    ].slice(0, 5),
  ),
  hero = computed(() => featured.value[index.value]),
  continuing = computed(() =>
    library.history.filter((h) => !h.completed && h.position > 0).slice(0, 4),
  );
async function load() {
  loading.value = true;
  error.value = "";
  sectionError.value = "";
  try {
    const { data } = await api.get<Catalog>("/anime/trending");
    trending.value = data.items;
    stale.value = !!data.stale;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
  const results = await Promise.allSettled([
    api.get<Catalog>("/anime/seasonal"),
    api.get<Catalog>("/anime/recent"),
  ]);
  results.forEach((r, i) => {
    if (r.status === "fulfilled") {
      (i === 0 ? seasonal : recent).value = r.value.data.items;
    } else sectionError.value = errorMessage(r.reason);
  });
  if (trending.value[0])
    try {
      recommended.value = (
        await api.get("/anime/" + trending.value[0].id + "/recommendations")
      ).data.items;
    } catch (e) {
      sectionError.value = errorMessage(e);
    }
}
onMounted(load);
onMounted(loadPlayable);
function cycle(direction: number) {
  index.value =
    (index.value + direction + featured.value.length) % featured.value.length;
}
</script>
<template>
  <section
    v-if="hero"
    class="hero"
    :style="{ '--hero-image': `url('${hero.banner || hero.cover}')` }"
  >
    <div class="hero-art"></div>
    <div class="hero-shade"></div>
    <div class="hero-content">
      <div class="eyebrow">
        <span class="live-dot"></span>PILIHAN MINGGU INI
      </div>
      <h1>{{ hero.title }}</h1>
      <div class="hero-meta">
        <span v-if="hero.score" class="rating"
          ><Star :size="15" fill="currentColor" />{{
            hero.score.toFixed(1)
          }}</span
        ><span v-if="hero.year">{{ hero.year }}</span
        ><span>{{ hero.format?.replaceAll("_", " ") }}</span
        ><span v-if="hero.episodes">{{ hero.episodes }} episode</span>
      </div>
      <p class="hero-description">{{ hero.description }}</p>
      <div class="hero-genres">
        <span v-for="genre in hero.genres.slice(0, 3)" :key="genre">{{
          genre
        }}</span>
      </div>
      <div class="hero-buttons">
        <RouterLink
          v-if="playable.some((p) => p.anime.id === hero.id)"
          :to="`/watch/${hero.id}/${playable.find((p) => p.anime.id === hero.id)!.episode}`"
          class="button"
          ><Play :size="18" fill="currentColor" />Tonton sekarang</RouterLink
        >
        <RouterLink :to="'/anime/' + hero.id" class="button"
          >Jelajahi anime <ArrowRight :size="18" /></RouterLink
        ><button
          class="button secondary"
          @click="
            library.has(hero.id) ? library.remove(hero.id) : library.save(hero)
          "
        >
          <Check v-if="library.has(hero.id)" :size="18" /><Bookmark
            v-else
            :size="18"
          />{{ library.has(hero.id) ? "Tersimpan" : "Watchlist" }}
        </button>
      </div>
    </div>
    <div class="hero-bottom">
      <span class="hero-caption">CERITA BARU. DUNIA BARU.</span>
      <div class="hero-controls">
        <button
          class="icon-button"
          aria-label="Anime sebelumnya"
          @click="cycle(-1)"
        >
          <ChevronLeft :size="18" /></button
        ><button
          v-for="(a, i) in featured"
          :key="a.id"
          class="slide-dot"
          :class="{ selected: index === i }"
          @click="index = i"
          :aria-label="'Tampilkan ' + a.title"
          :aria-current="index === i"
        ></button
        ><button
          class="icon-button"
          aria-label="Anime berikutnya"
          @click="cycle(1)"
        >
          <ChevronRight :size="18" /></button
        ><span class="slide-counter"
          >{{ String(index + 1).padStart(2, "0") }}
          <span>/ {{ String(featured.length).padStart(2, "0") }}</span></span
        >
      </div>
    </div>
  </section>
  <div v-else class="container home-loading">
    <LoadState :loading="loading" :error="error" @retry="load" />
  </div>
  <div class="container home-content">
    <AnimeSection
      v-if="playable.length"
      title="Anime dengan sumber video"
      subtitle="Pilih judul untuk melihat episode. Pemutaran mengikuti izin dan wilayah penyedia."
      :items="playable.map((p) => p.anime)"
    />
    <div class="browse-strip">
      <span>Temukan cerita berikutnya</span>
      <div>
        <RouterLink
          v-for="genre in [
            'Action',
            'Adventure',
            'Fantasy',
            'Romance',
            'Slice of Life',
          ]"
          :key="genre"
          :to="{ path: '/anime', query: { genre } }"
          >{{ genre }}</RouterLink
        ><RouterLink to="/anime" class="all-genres"
          >Semua genre <ArrowRight :size="15"
        /></RouterLink>
      </div>
    </div>
    <p v-if="stale" class="notice">
      Menampilkan metadata tersimpan. Penyedia sedang tidak tersedia.
    </p>
    <section v-if="continuing.length" class="anime-section">
      <div class="section-heading">
        <div>
          <h2>Lanjutkan ceritamu</h2>
          <p>Kembali ke bagian terakhir yang kamu tonton.</p>
        </div>
        <RouterLink to="/history" class="text-link"
          >Riwayat <ArrowRight :size="16"
        /></RouterLink>
      </div>
      <div class="continue-grid">
        <RouterLink
          v-for="h in continuing"
          :key="h.episode_id"
          :to="`/watch/${h.anime_id}/${h.episode}`"
          class="continue-card"
          ><img :src="h.anime.banner || h.anime.cover" :alt="h.anime.title" />
          <div class="continue-overlay">
            <Play :size="26" />
            <h3>{{ h.anime.title }}</h3>
            <span
              >Episode {{ h.episode }} ·
              {{ Math.floor(h.position / 60) }} menit</span
            >
          </div>
          <progress
            :value="h.position"
            :max="h.duration || 1"
            aria-label="Progres menonton"
        /></RouterLink>
      </div>
    </section>
    <AnimeSection
      v-if="trending.length"
      title="Sedang jadi perbincangan"
      subtitle="Anime yang sedang ramai ditonton komunitas."
      :items="trending.slice(0, 6)"
      to="/anime?sort=POPULARITY_DESC"
      ranked
    />
    <AnimeSection
      v-if="seasonal.length"
      title="Pilihan musim ini"
      subtitle="Ikuti cerita yang baru dimulai."
      :items="seasonal.slice(0, 6)"
      to="/anime?current=1"
    />
    <div class="discovery-banner">
      <div class="discovery-icon"><Clock3 :size="28" /></div>
      <div>
        <span class="eyebrow">JANGAN KETINGGALAN EPISODE</span>
        <h2>Selalu ada cerita untuk ditunggu.</h2>
        <p>Lihat jadwal rilis anime favoritmu, dalam waktu lokal.</p>
      </div>
      <RouterLink to="/schedule" class="button secondary"
        >Lihat jadwal <ArrowRight :size="17"
      /></RouterLink>
    </div>
    <AnimeSection
      v-if="recent.length"
      title="Baru hadir"
      subtitle="Rilisan terbaru untuk masuk watchlist-mu."
      :items="recent.slice(0, 6)"
      to="/anime?sort=START_DATE_DESC"
    />
    <AnimeSection
      v-if="recommended.length"
      title="Cerita lain yang mungkin kamu suka"
      :subtitle="'Rekomendasi komunitas berdasarkan ' + trending[0]?.title"
      :items="recommended.slice(0, 6)"
    />
    <div v-if="sectionError" class="notice">
      Beberapa koleksi belum bisa dimuat.
      <button @click="load">Coba lagi</button>
    </div>
    <div class="end-note">
      <span></span>
      <p>Masih banyak dunia untuk dijelajahi.</p>
      <RouterLink to="/anime"
        >Temukan anime berikutnya <ArrowRight :size="16"
      /></RouterLink>
    </div>
  </div>
</template>

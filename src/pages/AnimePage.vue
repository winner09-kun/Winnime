<script setup lang="ts">
import { ref, watch, computed, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  Search,
  SlidersHorizontal,
  ArrowLeft,
  ArrowRight,
  X,
} from "lucide-vue-next";
import { api, errorMessage } from "../services/api";
import type { Anime, Catalog } from "../types";
import AnimeCard from "../components/AnimeCard.vue";
import LoadState from "../components/LoadState.vue";
const route = useRoute(),
  router = useRouter(),
  items = ref<Anime[]>([]),
  loading = ref(false),
  error = ref(""),
  hasNext = ref(false),
  term = ref(String(route.query.search || "")),
  filtersOpen = ref(false);
let timer: ReturnType<typeof setTimeout>,
  controller: AbortController | undefined;
const page = computed(() => Math.max(1, Number(route.query.page) || 1)),
  genres = [
    "Action",
    "Adventure",
    "Comedy",
    "Drama",
    "Fantasy",
    "Horror",
    "Mahou Shoujo",
    "Mecha",
    "Music",
    "Mystery",
    "Psychological",
    "Romance",
    "Sci-Fi",
    "Slice of Life",
    "Sports",
    "Supernatural",
    "Thriller",
  ],
  years = Array.from(
    { length: 70 },
    (_, i) => new Date().getFullYear() + 1 - i,
  );
function update(key: string, value: string) {
  const seasonal = route.query.current
    ? {
        year: String(new Date().getFullYear()),
        season: ["WINTER", "SPRING", "SUMMER", "FALL"][
          Math.floor(new Date().getMonth() / 3)
        ],
      }
    : {};
  const q = {
    ...seasonal,
    ...route.query,
    [key]: value || undefined,
    page: undefined,
    current: undefined,
  };
  router.replace({ query: q });
}
function input() {
  clearTimeout(timer);
  timer = setTimeout(() => update("search", term.value), 350);
}
async function load() {
  controller?.abort();
  controller = new AbortController();
  const own = controller;
  loading.value = true;
  error.value = "";
  try {
    const params = { ...route.query };
    if (params.current) {
      params.year = String(new Date().getFullYear());
      params.season = ["WINTER", "SPRING", "SUMMER", "FALL"][
        Math.floor(new Date().getMonth() / 3)
      ];
    }
    const { data } = await api.get<Catalog>("/anime/search", {
      params,
      signal: own.signal,
    });
    items.value = data.items;
    hasNext.value = data.has_next;
  } catch (e) {
    if (!own.signal.aborted) error.value = errorMessage(e);
  } finally {
    if (!own.signal.aborted) loading.value = false;
  }
}
watch(
  () => route.query,
  () => {
    term.value = String(route.query.search || "");
    load();
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  clearTimeout(timer);
  controller?.abort();
});
</script>
<template>
  <div class="container page">
    <div class="page-heading">
      <div>
        <div class="eyebrow">TEMUKAN FAVORIT BARUMU</div>
        <h1>Jelajahi anime</h1>
        <p>Dari cerita yang melegenda sampai yang baru dimulai.</p>
      </div>
    </div>
    <div class="catalog-search">
      <Search :size="21" /><input
        v-model="term"
        @input="input"
        placeholder="Cari judul anime…"
        aria-label="Cari judul anime"
      /><button
        v-if="term"
        class="icon-button"
        aria-label="Hapus pencarian"
        @click="
          term = '';
          update('search', '');
        "
      >
        <X :size="18" /></button
      ><button
        class="button secondary filter-toggle"
        @click="filtersOpen = !filtersOpen"
      >
        <SlidersHorizontal :size="16" />Filter
      </button>
    </div>
    <div class="filter-panel" :class="{ expanded: filtersOpen }">
      <label
        >Genre<select
          :value="route.query.genre || ''"
          @change="update('genre', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Semua genre</option>
          <option v-for="g in genres" :key="g">{{ g }}</option>
        </select></label
      ><label
        >Tahun<select
          :value="route.query.year || ''"
          @change="update('year', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Semua tahun</option>
          <option v-for="y in years" :key="y">{{ y }}</option>
        </select></label
      ><label
        >Musim<select
          :value="route.query.season || ''"
          @change="update('season', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Semua musim</option>
          <option value="WINTER">Winter</option>
          <option value="SPRING">Spring</option>
          <option value="SUMMER">Summer</option>
          <option value="FALL">Fall</option>
        </select></label
      ><label
        >Format<select
          :value="route.query.format || ''"
          @change="update('format', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Semua format</option>
          <option
            v-for="f in ['TV', 'MOVIE', 'OVA', 'ONA', 'SPECIAL']"
            :key="f"
          >
            {{ f }}
          </option>
        </select></label
      ><label
        >Status<select
          :value="route.query.status || ''"
          @change="update('status', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Semua status</option>
          <option value="RELEASING">Sedang tayang</option>
          <option value="FINISHED">Selesai</option>
          <option value="NOT_YET_RELEASED">Segera hadir</option>
        </select></label
      ><button class="reset-filter" @click="router.replace('/anime')">
        Reset filter
      </button>
    </div>
    <div class="results-bar">
      <p>
        {{
          loading
            ? "Mencari anime…"
            : items.length + " anime di halaman " + page
        }}
      </p>
      <label
        >Urutkan<select
          aria-label="Urutkan anime"
          :value="route.query.sort || 'POPULARITY_DESC'"
          @change="update('sort', ($event.target as HTMLSelectElement).value)"
        >
          <option value="POPULARITY_DESC">Paling populer</option>
          <option value="SCORE_DESC">Rating tertinggi</option>
          <option value="START_DATE_DESC">Rilisan terbaru</option>
          <option value="TITLE_ROMAJI">Judul A–Z</option>
        </select></label
      >
    </div>
    <LoadState
      :loading="loading"
      :error="error"
      :empty="!items.length"
      @retry="load"
    />
    <div v-if="!loading && !error" class="anime-grid catalog-grid">
      <AnimeCard v-for="a in items" :key="a.id" :anime="a" />
    </div>
    <div v-if="!loading && !error && (hasNext || page > 1)" class="pagination">
      <button
        class="button secondary"
        :disabled="page <= 1"
        @click="router.push({ query: { ...route.query, page: page - 1 } })"
      >
        <ArrowLeft :size="16" />Sebelumnya</button
      ><span>{{ page }}</span
      ><button
        class="button secondary"
        :disabled="!hasNext"
        @click="router.push({ query: { ...route.query, page: page + 1 } })"
      >
        Berikutnya<ArrowRight :size="16" />
      </button>
    </div>
  </div>
</template>

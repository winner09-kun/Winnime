<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import {
  Bookmark,
  History,
  ArrowRight,
  Trash2,
  Play,
  RotateCcw,
} from "lucide-vue-next";
import { useLibrary, statuses } from "../stores/library";
import type { WatchStatus } from "../types";
import AnimeCard from "../components/AnimeCard.vue";
const route = useRoute(),
  library = useLibrary(),
  filter = ref(""),
  confirmClear = ref(false),
  sort = ref("recent");
const historyMode = computed(() => route.path === "/history"),
  items = computed(() =>
    library.watchlist
      .filter(
        (w) =>
          (!filter.value || w.status === filter.value) &&
          (library.settings.show_completed || w.status !== "COMPLETED"),
      )
      .sort((a, b) =>
        sort.value === "title"
          ? a.anime.title.localeCompare(b.anime.title)
          : sort.value === "status"
            ? a.status.localeCompare(b.status)
            : b.updated_at - a.updated_at,
      ),
  );
onMounted(library.load);
</script>
<template>
  <div class="container page">
    <div class="page-heading split">
      <div>
        <div class="eyebrow">KOLEKSI PRIBADIMU</div>
        <h1>{{ historyMode ? "Riwayat menonton" : "Watchlist" }}</h1>
        <p>
          {{
            historyMode
              ? "Setiap cerita yang pernah kamu mulai."
              : "Simpan sekarang. Nikmati saat waktunya tepat."
          }}
        </p>
      </div>
      <RouterLink
        :to="historyMode ? '/watchlist' : '/history'"
        class="button secondary"
        ><Bookmark v-if="historyMode" :size="17" /><History
          v-else
          :size="17"
        />{{ historyMode ? "Watchlist" : "Riwayat" }}</RouterLink
      >
    </div>
    <div v-if="library.error" class="notice" role="alert">
      {{ library.error }} <button @click="library.load">Coba lagi</button>
    </div>
    <template v-else-if="historyMode"
      ><div v-if="library.history.length" class="results-bar">
        <span>{{ library.history.length }} episode</span
        ><button class="text-link" @click="confirmClear = true">
          <Trash2 :size="15" />Hapus semua riwayat
        </button>
      </div>
      <div v-if="confirmClear" class="confirm-panel">
        <p>Hapus semua progres dan riwayat menonton?</p>
        <button
          class="button small"
          @click="
            library.reset();
            confirmClear = false;
          "
        >
          Hapus riwayat</button
        ><button class="button secondary small" @click="confirmClear = false">
          Batal
        </button>
      </div>
      <article
        v-for="h in library.history"
        :key="h.episode_id"
        class="history-row"
      >
        <RouterLink :to="'/anime/' + h.anime_id"
          ><img :src="h.anime.cover" :alt="h.anime.title"
        /></RouterLink>
        <div>
          <RouterLink :to="'/anime/' + h.anime_id"
            ><h2>{{ h.anime.title }}</h2></RouterLink
          >
          <p>
            Episode {{ h.episode }} ·
            {{
              h.completed
                ? "Selesai"
                : Math.floor(h.position / 60) + " menit ditonton"
            }}
          </p>
          <progress
            :value="h.completed ? 1 : h.position"
            :max="h.completed ? 1 : h.duration || 1"
            aria-label="Progres menonton"
          /><small>{{
            new Date(h.updated_at * 1000).toLocaleString("id-ID")
          }}</small>
        </div>
        <RouterLink
          class="button secondary small"
          :to="`/watch/${h.anime_id}/${h.episode}`"
          ><Play :size="15" />Lanjutkan</RouterLink
        ><button
          class="icon-button"
          @click="library.reset(h.episode_id)"
          aria-label="Reset progres episode"
        >
          <RotateCcw :size="17" />
        </button>
      </article>
      <div v-if="!library.history.length" class="empty-state">
        <History :size="36" />
        <h2>Ceritamu belum dimulai</h2>
        <p>Episode yang kamu tonton akan tersimpan otomatis di sini.</p>
        <RouterLink to="/anime" class="button"
          >Jelajahi anime <ArrowRight :size="17"
        /></RouterLink></div></template
    ><template v-else
      ><div class="library-controls">
        <div class="tabs">
          <button :class="{ active: !filter }" @click="filter = ''">
            Semua <span>{{ library.watchlist.length }}</span></button
          ><button
            v-for="(label, key) in statuses"
            :key="key"
            :class="{ active: filter === key }"
            @click="filter = key"
          >
            {{ label }}
          </button>
        </div>
        <select v-model="sort" aria-label="Urutkan watchlist">
          <option value="recent">Terakhir ditambahkan</option>
          <option value="title">Judul A–Z</option>
          <option value="status">Status</option>
        </select>
      </div>
      <div v-if="items.length" class="anime-grid">
        <div v-for="w in items" :key="w.anime_id">
          <AnimeCard :anime="w.anime" /><select
            class="status-select"
            aria-label="Status menonton"
            :value="w.status"
            @change="
              library.save(
                w.anime,
                ($event.target as HTMLSelectElement).value as WatchStatus,
              )
            "
          >
            <option v-for="(label, key) in statuses" :key="key" :value="key">
              {{ label }}
            </option>
          </select>
          <p class="muted progress-label">
            {{
              library.history.filter(
                (h) => h.anime_id === w.anime_id && h.completed,
              ).length
            }}
            episode selesai
          </p>
        </div>
      </div>
      <div v-else class="empty-state">
        <Bookmark :size="36" />
        <h2>
          {{
            filter
              ? "Belum ada anime di kategori ini"
              : "Ruang untuk cerita favoritmu"
          }}
        </h2>
        <p>Tekan ikon bookmark pada anime untuk menyimpannya di sini.</p>
        <RouterLink to="/anime" class="button"
          >Temukan anime <ArrowRight :size="17"
        /></RouterLink></div
    ></template>
  </div>
</template>

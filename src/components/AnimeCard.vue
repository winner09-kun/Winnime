<script setup lang="ts">
import { ref } from "vue";
import { Bookmark, Check, Star, ImageOff } from "lucide-vue-next";
import type { Anime } from "../types";
import { useLibrary } from "../stores/library";
defineProps<{ anime: Anime; rank?: number }>();
const library = useLibrary(),
  failed = ref(false);
</script>
<template>
  <article class="anime-card">
    <div class="poster-wrap">
      <RouterLink
        :to="'/anime/' + anime.id"
        :aria-label="'Lihat ' + anime.title"
        class="poster-link"
        ><img
          v-if="anime.cover && !failed"
          :src="anime.cover"
          :alt="anime.title"
          loading="lazy"
          @error="failed = true"
        />
        <div v-else class="poster-fallback">
          <ImageOff /><span>{{ anime.title }}</span>
        </div>
        <span v-if="rank" class="rank-label">{{
          String(rank).padStart(2, "0")
        }}</span
        ><span v-if="anime.score" class="score"
          ><Star :size="12" fill="currentColor" />
          {{ anime.score.toFixed(1) }}</span
        >
        <div class="card-hover">
          <span>{{ anime.genres?.slice(0, 2).join(" · ") }}</span
          ><span>Lihat detail →</span>
        </div></RouterLink
      ><button
        class="save-button"
        :class="{ saved: library.has(anime.id) }"
        @click="
          library.has(anime.id) ? library.remove(anime.id) : library.save(anime)
        "
        :aria-label="
          library.has(anime.id)
            ? 'Hapus ' + anime.title + ' dari watchlist'
            : 'Simpan ' + anime.title
        "
      >
        <Check v-if="library.has(anime.id)" :size="17" /><Bookmark
          v-else
          :size="17"
        />
      </button>
    </div>
    <RouterLink :to="'/anime/' + anime.id" class="card-title">{{
      anime.title
    }}</RouterLink>
    <p class="card-meta">
      {{ anime.format?.replaceAll("_", " ") || "Anime" }}<span>•</span
      >{{
        anime.episodes
          ? anime.episodes + " episode"
          : anime.year || "Info belum tersedia"
      }}
    </p>
  </article>
</template>

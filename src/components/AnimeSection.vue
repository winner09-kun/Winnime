<script setup lang="ts">
import { ArrowRight } from "lucide-vue-next";
import type { Anime } from "../types";
import AnimeCard from "./AnimeCard.vue";
defineProps<{
  title: string;
  subtitle?: string;
  items: Anime[];
  to?: string;
  ranked?: boolean;
}>();
</script>
<template>
  <section class="anime-section">
    <div class="section-heading">
      <div>
        <h2>{{ title }}</h2>
        <p v-if="subtitle">{{ subtitle }}</p>
      </div>
      <RouterLink v-if="to" :to="to" class="text-link"
        >Lihat semua <ArrowRight :size="16"
      /></RouterLink>
    </div>
    <div class="anime-grid">
      <AnimeCard
        v-for="(anime, i) in items"
        :key="anime.id"
        :anime="anime"
        :rank="ranked ? i + 1 : undefined"
      />
    </div>
  </section>
</template>

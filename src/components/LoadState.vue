<script setup lang="ts">
import { RefreshCw, SearchX } from "lucide-vue-next";
defineProps<{ loading?: boolean; error?: string; empty?: boolean }>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div
    v-if="loading"
    aria-busy="true"
    aria-label="Memuat anime"
    class="anime-grid skeleton-grid"
  >
    <div v-for="i in 6" :key="i">
      <div class="skeleton poster-skeleton"></div>
      <div class="skeleton line-skeleton"></div>
    </div>
  </div>
  <div v-else-if="error" class="empty-state" role="alert">
    <RefreshCw />
    <h2>Belum bisa memuat</h2>
    <p>{{ error }}</p>
    <button class="button secondary" @click="$emit('retry')">
      <RefreshCw :size="16" />Coba lagi
    </button>
  </div>
  <div v-else-if="empty" class="empty-state">
    <SearchX />
    <h2>Tidak ada anime ditemukan</h2>
    <p>Coba kata kunci lain atau kurangi filter pencarian.</p>
  </div>
</template>

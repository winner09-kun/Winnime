<script setup lang="ts" generic="T extends EpisodeFilterItem">
import { computed, ref } from 'vue';
import { filterEpisodes, type EpisodeFilterItem } from '../services/episodeFilter';

const props = defineProps<{
  items: T[];
  availability?: boolean;
  completedNumbers?: number[];
  hasMore?: boolean;
}>();
const query = ref(''), status = ref('all');
const filtered = computed(() => filterEpisodes(props.items, query.value, status.value, props.completedNumbers));
function reset() { query.value = ''; status.value = 'all'; }
</script>

<template>
  <div class="episode-filters">
    <label>Cari episode
      <input v-model="query" type="search" placeholder="Nomor atau judul episode" />
    </label>
    <label v-if="availability || completedNumbers !== undefined">Status episode
      <select v-model="status">
        <option value="all">Semua episode</option>
        <option v-if="availability" value="available">Tersedia</option>
        <option v-if="availability" value="unavailable">Belum tersedia</option>
        <option v-if="completedNumbers !== undefined" value="completed">Sudah ditonton</option>
        <option v-if="completedNumbers !== undefined" value="unwatched">Belum selesai ditonton</option>
      </select>
    </label>
    <button v-if="query || status !== 'all'" type="button" class="text-link" @click="reset">Reset filter</button>
    <p class="muted filter-count" role="status">{{ filtered.length }} dari {{ items.length }} episode yang dimuat</p>
    <p v-if="hasMore" class="muted filter-count">Filter berlaku untuk episode yang sudah dimuat. Gunakan “Muat episode berikutnya” untuk mencari lebih banyak.</p>
    <p v-if="items.length && !filtered.length" class="notice filter-count">Tidak ada episode yang cocok. Coba kata lain atau reset filter.</p>
  </div>
  <slot :items="filtered" />
</template>

<style scoped>
.episode-filters { display: flex; flex-wrap: wrap; align-items: end; gap: 12px; margin: 16px 0; }
label { display: flex; flex: 1 1 170px; flex-direction: column; gap: 6px; min-width: 0; font-size: 13px; }
input, select { width: 100%; min-width: 0; }
.filter-count { flex-basis: 100%; margin: 0; font-size: 13px; }
</style>

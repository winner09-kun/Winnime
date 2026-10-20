<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { CalendarDays, ArrowRight } from "lucide-vue-next";
import { api, errorMessage } from "../services/api";
import type { Anime } from "../types";
import LoadState from "../components/LoadState.vue";
const anime = ref<Anime[]>([]),
  loading = ref(true),
  error = ref(""),
  day = ref(0),
  dates = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return d;
  }),
  zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
const items = computed(() =>
  anime.value
    .filter(
      (a) =>
        a.next_episode &&
        new Date(a.next_episode.airingAt * 1000).toDateString() ===
          dates[day.value]!.toDateString(),
    )
    .sort((a, b) => a.next_episode!.airingAt - b.next_episode!.airingAt),
);
async function load() {
  loading.value = true;
  error.value = "";
  try {
    const pages = await Promise.all(
      [1, 2, 3].map((page) =>
        api.get("/anime/search", { params: { status: "RELEASING", page } }),
      ),
    );
    anime.value = pages.flatMap((r) => r.data.items);
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>
<template>
  <div class="container page">
    <div class="page-heading">
      <div class="eyebrow">CATAT WAKTUNYA</div>
      <h1>Jadwal rilis</h1>
      <p>
        Episode berikutnya dari anime yang sedang tayang. Zona waktu {{ zone }}.
      </p>
    </div>
    <div class="schedule-days">
      <button
        v-for="(d, i) in dates"
        :key="i"
        :class="{ active: day === i }"
        @click="day = i"
      >
        <span>{{
          i === 0
            ? "Hari ini"
            : d.toLocaleDateString("id-ID", { weekday: "short" })
        }}</span
        ><strong>{{ d.getDate() }}</strong
        ><small>{{ d.toLocaleDateString("id-ID", { month: "short" }) }}</small>
      </button>
    </div>
    <p class="schedule-note">
      Jadwal dari AniList untuk 54 anime terpopuler yang sedang tayang. Waktu
      rilis dapat berubah dan berbeda dari ketersediaan di penyedia video.
    </p>
    <LoadState :loading="loading" :error="error" @retry="load" />
    <div v-if="!loading && !error" class="schedule-grid">
      <RouterLink
        v-for="a in items"
        :key="a.id"
        :to="'/anime/' + a.id"
        class="schedule-card"
        ><img :src="a.cover" :alt="a.title" loading="lazy" />
        <div>
          <span class="schedule-time">{{
            new Date(a.next_episode!.airingAt * 1000).toLocaleTimeString(
              "id-ID",
              { hour: "2-digit", minute: "2-digit" },
            )
          }}</span>
          <h2>{{ a.title }}</h2>
          <p>Episode {{ a.next_episode!.episode }}</p>
          <span class="text-link"
            >Lihat anime <ArrowRight :size="14"
          /></span></div
      ></RouterLink>
    </div>
    <div v-if="!loading && !error && !items.length" class="empty-state">
      <CalendarDays :size="36" />
      <h2>Belum ada jadwal untuk hari ini</h2>
      <p>Coba hari lain untuk melihat episode yang akan datang.</p>
    </div>
  </div>
</template>

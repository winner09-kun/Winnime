<script setup lang="ts">
import {
  ref,
  onMounted,
  onBeforeUnmount,
  onErrorCaptured,
  nextTick,
} from "vue";
import { useRouter } from "vue-router";
import {
  Search,
  Bookmark,
  Settings,
  Menu,
  X,
  Wind,
  ArrowUpRight,
} from "lucide-vue-next";
import { useLibrary } from "./stores/library";
const library = useLibrary(),
  router = useRouter(),
  mobile = ref(false),
  searchOpen = ref(false),
  term = ref(""),
  crash = ref("");
onMounted(library.load);
function shortcut(event: KeyboardEvent) {
  if (
    event.key === "/" &&
    !["INPUT", "TEXTAREA", "SELECT"].includes(
      (event.target as HTMLElement).tagName,
    )
  ) {
    event.preventDefault();
    searchOpen.value = true;
    nextTick(() =>
      document.querySelector<HTMLInputElement>(".header-search input")?.focus(),
    );
  }
  if (event.key === "Escape") searchOpen.value = false;
}
onMounted(() => window.addEventListener("keydown", shortcut));
onBeforeUnmount(() => window.removeEventListener("keydown", shortcut));
onErrorCaptured((e) => {
  crash.value =
    "Halaman tidak dapat ditampilkan. Muat ulang untuk mencoba lagi.";
  console.error(e);
  return false;
});
router.afterEach(() => {
  mobile.value = false;
  crash.value = "";
});
function search() {
  searchOpen.value = false;
  router.push({
    path: "/anime",
    query: term.value ? { search: term.value } : {},
  });
}
function reload() {
  window.location.reload();
}
</script>
<template>
  <a class="skip-link" href="#main">Lewati ke konten</a>
  <header class="site-header">
    <div class="nav-inner">
      <RouterLink to="/" class="brand" aria-label="WINNIME beranda"
        ><Wind :size="29" stroke-width="2.6" /><span
          >WINNIME<span class="brand-dot">.</span></span
        ></RouterLink
      >
      <nav class="desktop-nav" aria-label="Navigasi utama">
        <RouterLink to="/" exact-active-class="active">Beranda</RouterLink
        ><RouterLink to="/anime" active-class="active">Jelajahi</RouterLink
        ><RouterLink to="/streaming" active-class="active">Nonton</RouterLink
        ><RouterLink to="/schedule" active-class="active"
          >Jadwal rilis</RouterLink
        >
      </nav>
      <div class="nav-actions">
        <button
          class="search-trigger"
          @click="searchOpen = !searchOpen"
          aria-label="Cari anime"
        >
          <Search :size="19" /><span>Cari anime</span><kbd>/</kbd></button
        ><span class="nav-divider"></span
        ><RouterLink to="/watchlist" class="icon-button" aria-label="Watchlist"
          ><Bookmark :size="21" /></RouterLink
        ><RouterLink
          to="/settings"
          class="icon-button settings-link"
          aria-label="Pengaturan"
          ><Settings :size="21" /></RouterLink
        ><button
          class="icon-button mobile-toggle"
          @click="mobile = !mobile"
          :aria-expanded="mobile"
          aria-label="Buka navigasi"
        >
          <X v-if="mobile" /><Menu v-else />
        </button>
      </div>
    </div>
    <nav v-if="mobile" class="mobile-nav" aria-label="Navigasi seluler">
      <RouterLink to="/">Beranda</RouterLink
      ><RouterLink to="/anime">Jelajahi anime</RouterLink
      ><RouterLink to="/streaming">Nonton</RouterLink
      ><RouterLink to="/schedule">Jadwal rilis</RouterLink
      ><RouterLink to="/watchlist">Watchlist</RouterLink
      ><RouterLink to="/history">Riwayat</RouterLink
      ><RouterLink to="/settings">Pengaturan</RouterLink>
    </nav>
    <form v-if="searchOpen" class="header-search" @submit.prevent="search">
      <Search :size="20" /><input
        v-model="term"
        autofocus
        aria-label="Judul anime"
        placeholder="Judul Jepang, Romaji, atau Inggris…"
      /><button type="submit" class="button small">Cari</button
      ><button
        type="button"
        class="icon-button"
        @click="searchOpen = false"
        aria-label="Tutup pencarian"
      >
        <X :size="20" />
      </button>
    </form>
  </header>
  <main id="main">
    <div v-if="crash" class="empty-state">
      <h1>{{ crash }}</h1>
      <button class="button" @click="reload">Muat ulang</button>
    </div>
    <RouterView v-else :key="$route.path.startsWith('/streaming') ? $route.fullPath : $route.path" />
  </main>
  <footer class="site-footer">
    <div class="footer-top">
      <RouterLink to="/" class="brand"
        ><Wind :size="25" /><span>WINNIME.</span></RouterLink
      >
      <p>Anime, at your pace.</p>
      <div>
        <RouterLink to="/watchlist">Watchlist</RouterLink
        ><RouterLink to="/history">Riwayat</RouterLink
        ><RouterLink to="/settings"
          >Pengaturan <ArrowUpRight :size="14"
        /></RouterLink>
      </div>
    </div>
    <div class="footer-bottom">
      <span>Ruang anime pribadi. Tanpa akun, tanpa distraksi.</span
      ><span
        >Metadata oleh
        <a href="https://anilist.co" target="_blank" rel="noreferrer"
          >AniList</a
        >
        &
        <a href="https://jikan.moe" target="_blank" rel="noreferrer"
          >Jikan</a
        ></span
      >
    </div>
  </footer>
  <div v-if="library.toast" class="toast" role="status">
    {{ library.toast }}
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Plus, Trash2, Check, Database, ExternalLink } from "lucide-vue-next";
import { api, errorMessage } from "../services/api";
import { useLibrary } from "../stores/library";
import type { Source } from "../types";
const library = useLibrary(),
  sources = ref<Source[]>([]),
  error = ref(""),
  saving = ref(false),
  authorized = ref(false),
  form = ref({
    anime_id: 0,
    episode: 1,
    provider: "youtube",
    url: "",
    language: "Japanese",
  }),
  subtitle = ref({ url: "", language: "id", label: "Indonesia" }),
  confirmDelete = ref<number>();
async function load() {
  try {
    sources.value = (await api.get("/sources")).data;
    error.value = "";
  } catch (e) {
    error.value = errorMessage(e);
  }
}
async function saveSettings() {
  saving.value = true;
  try {
    library.settings = (await api.patch("/settings", library.settings)).data;
    library.notify("Pengaturan disimpan");
  } catch (e) {
    library.notify(errorMessage(e));
  } finally {
    saving.value = false;
  }
}
async function add() {
  saving.value = true;
  error.value = "";
  try {
    const { data } = await api.post("/sources", {
      ...form.value,
      authorized: authorized.value,
      available: true,
      subtitles: subtitle.value.url ? [subtitle.value] : [],
    });
    sources.value.push(data);
    form.value.url = "";
    subtitle.value.url = "";
    authorized.value = false;
    library.notify("Sumber video ditambahkan");
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    saving.value = false;
  }
}
async function remove(id: number) {
  try {
    await api.delete("/sources/" + id);
    sources.value = sources.value.filter((s) => s.id !== id);
    confirmDelete.value = undefined;
    library.notify("Sumber video dihapus");
  } catch (e) {
    error.value = errorMessage(e);
  }
}
onMounted(() => {
  library.load();
  load();
});
</script>
<template>
  <div class="container page settings-page">
    <div class="page-heading">
      <div class="eyebrow">SESUAI CARAMU</div>
      <h1>Pengaturan</h1>
      <p>Atur pengalaman menonton dan perpustakaan video pribadimu.</p>
    </div>
    <section class="settings-section">
      <div>
        <h2>Preferensi menonton</h2>
        <p>Disimpan di database lokal perangkat ini.</p>
      </div>
      <form @submit.prevent="saveSettings">
        <label class="toggle-row"
          ><span
            ><strong>Putar otomatis</strong
            ><small
              >Mulai video saat halaman menonton dibuka, jika browser
              mengizinkan.</small
            ></span
          ><input type="checkbox" v-model="library.settings.autoplay" /></label
        ><label class="toggle-row"
          ><span
            ><strong>Lanjut ke episode berikutnya</strong
            ><small
              >Hanya untuk episode dengan sumber video tersedia.</small
            ></span
          ><input type="checkbox" v-model="library.settings.auto_next" /></label
        ><label class="toggle-row"
          ><span
            ><strong>Tampilkan anime selesai</strong
            ><small
              >Sertakan anime yang sudah selesai di watchlist.</small
            ></span
          ><input
            type="checkbox"
            v-model="library.settings.show_completed" /></label
        ><button class="button small" :disabled="saving">
          <Check :size="16" />Simpan preferensi
        </button>
      </form>
    </section>
    <section class="settings-section">
      <div>
        <h2>Sumber video</h2>
        <p>
          Hubungkan anime dengan video berizin milikmu. Metadata anime tidak
          menyediakan stream episode.
        </p>
      </div>
      <div>
        <div v-if="error" class="notice" role="alert">
          {{ error }} <button @click="load">Coba lagi</button>
        </div>
        <div v-if="!sources.length" class="source-empty">
          <Database :size="24" />
          <p>
            Belum ada sumber video. Tambahkan video untuk mengaktifkan
            pemutaran.
          </p>
        </div>
        <article v-for="s in sources" :key="s.id" class="source-row">
          <div>
            <RouterLink :to="'/anime/' + s.anime_id"
              ><strong
                >Anime {{ s.anime_id }} · Episode {{ s.episode }}</strong
              ></RouterLink
            ><small>{{ s.provider.toUpperCase() }} · {{ s.language }}</small
            ><a :href="`/watch/${s.anime_id}/${s.episode}`" class="text-link"
              >Buka player <ExternalLink :size="13"
            /></a>
          </div>
          <button
            class="icon-button"
            aria-label="Hapus sumber video"
            @click="confirmDelete = s.id"
          >
            <Trash2 :size="17" />
          </button>
          <div v-if="confirmDelete === s.id" class="inline-confirm">
            <span>Hapus sumber?</span
            ><button class="text-link" @click="remove(s.id)">Hapus</button
            ><button class="text-link" @click="confirmDelete = undefined">
              Batal
            </button>
          </div>
        </article>
        <form class="source-form" @submit.prevent="add">
          <h3>Tambah sumber video</h3>
          <div class="form-grid">
            <label
              >AniList ID<input
                type="number"
                min="1"
                required
                v-model.number="form.anime_id"
              /><small>Lihat ID di halaman detail anime.</small></label
            ><label
              >Episode<input
                type="number"
                min="1"
                required
                v-model.number="form.episode" /></label
            ><label
              >Provider<select v-model="form.provider">
                <option value="youtube">YouTube</option>
                <option value="mp4">MP4 pribadi</option>
                <option value="hls">HLS berizin</option>
                <option value="cloudflare">Cloudflare Stream (opsional)</option>
              </select></label
            ><label
              >Bahasa audio<input v-model="form.language" required
            /></label>
          </div>
          <label
            >{{
              form.provider === "youtube"
                ? "YouTube video ID"
                : form.provider === "cloudflare"
                  ? "Cloudflare Stream UID"
                  : "URL video (HTTPS atau server lokal)"
            }}<input
              v-model="form.url"
              required
              :placeholder="
                form.provider === 'youtube'
                  ? 'ID video, 11 karakter'
                  : 'URL atau UID sesuai provider'
              " /></label
          ><template v-if="form.provider === 'mp4' || form.provider === 'hls'"
            ><label
              >URL subtitle WebVTT (opsional)<input
                type="url"
                v-model="subtitle.url"
                placeholder="https://…/subtitle.vtt"
            /></label>
            <div v-if="subtitle.url" class="form-grid">
              <label
                >Bahasa subtitle<input
                  v-model="subtitle.language"
                  required /></label
              ><label
                >Label subtitle<input v-model="subtitle.label" required
              /></label>
            </div>
            <p class="muted">
              Server media harus mengizinkan CORS dari alamat WINNIME. Gunakan
              server lokal untuk file di perangkatmu.
            </p></template
          >
          <p v-if="form.provider === 'youtube'" class="muted">
            Gunakan video dari kanal resmi yang mengizinkan embedding.
            Ketersediaan ditentukan oleh YouTube.
          </p>
          <p v-if="form.provider === 'cloudflare'" class="muted">
            Adapter hosted opsional ini belum mendukung penyimpanan progres
            otomatis.
          </p>
          <label class="checkbox-label"
            ><input type="checkbox" v-model="authorized" required /><span
              >Saya memiliki izin untuk memutar sumber video ini.</span
            ></label
          ><button class="button" :disabled="saving">
            <Plus :size="17" />{{ saving ? "Menyimpan…" : "Tambah sumber" }}
          </button>
        </form>
      </div>
    </section>
    <section class="settings-section">
      <div>
        <h2>Tentang WINNIME</h2>
        <p>Anime, at your pace.</p>
      </div>
      <p class="about-copy">
        Aplikasi anime pribadi tanpa akun. Watchlist, riwayat, dan pengaturan
        tersimpan di SQLite lokal. Katalog disediakan oleh AniList dengan
        metadata episode dari Jikan. Ketersediaan video bergantung pada sumber
        yang kamu konfigurasi.
      </p>
    </section>
  </div>
</template>

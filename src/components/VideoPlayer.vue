<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import Hls from "hls.js";
import type { Source } from "../types";
const props = defineProps<{
  source: Source;
  resume: number;
  autoplay: boolean;
}>();
const emit = defineEmits<{
  progress: [position: number, duration: number];
  ended: [];
  error: [message: string];
}>();
const video = ref<HTMLVideoElement>(),
  youtubeHost = ref<HTMLDivElement>(),
  rate = ref(1),
  qualities = ref<{ height: number; index: number }[]>([]),
  quality = ref(-1);
let hls: Hls | undefined,
  yt: any,
  timer: ReturnType<typeof setInterval> | undefined,
  disposed = false,
  lastSaved = 0;
const ytWindow = window as any;
function save() {
  if (video.value && video.value.readyState > 0)
    emit(
      "progress",
      video.value.currentTime,
      Number.isFinite(video.value.duration) ? video.value.duration : 0,
    );
  else if (yt?.getCurrentTime)
    emit("progress", yt.getCurrentTime(), yt.getDuration());
}
function timeupdate() {
  if (Date.now() - lastSaved > 10000) {
    save();
    lastSaved = Date.now();
  }
}
function metadata() {
  if (video.value && props.resume > 0)
    video.value.currentTime = Math.min(
      props.resume,
      video.value.duration || props.resume,
    );
}
function speed() {
  if (video.value) video.value.playbackRate = rate.value;
}
function setQuality() {
  if (hls) hls.currentLevel = quality.value;
}
function keyboard(event: KeyboardEvent) {
  const v = video.value;
  if (
    !v ||
    ["INPUT", "SELECT", "TEXTAREA"].includes(
      (event.target as HTMLElement).tagName,
    )
  )
    return;
  if (event.key === " " || event.key === "k") {
    event.preventDefault();
    v.paused ? v.play().catch(() => {}) : v.pause();
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    v.currentTime = Math.min(v.duration || 0, v.currentTime + 10);
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    v.currentTime = Math.max(0, v.currentTime - 10);
  }
  if (event.key === "f") v.requestFullscreen?.();
  if (event.key === "m") v.muted = !v.muted;
}
async function youtubeAPI() {
  if (ytWindow.YT?.Player) return;
  await new Promise<void>((resolve, reject) => {
    const previous = ytWindow.onYouTubeIframeAPIReady;
    ytWindow.onYouTubeIframeAPIReady = () => {
      previous?.();
      resolve();
    };
    if (
      !document.querySelector(
        'script[src="https://www.youtube.com/iframe_api"]',
      )
    ) {
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      script.onerror = () => reject(new Error("YouTube tidak dapat dimuat"));
      document.head.append(script);
    }
    setTimeout(
      () =>
        ytWindow.YT?.Player
          ? resolve()
          : reject(new Error("YouTube tidak merespons")),
      20000,
    );
  });
}
onMounted(async () => {
  window.addEventListener("pagehide", save);
  document.addEventListener("visibilitychange", visibilitySave);
  if (props.source.provider === "youtube") {
    try {
      await youtubeAPI();
      if (disposed) return;
      yt = new ytWindow.YT.Player(youtubeHost.value, {
        videoId: props.source.url,
        playerVars: {
          autoplay: props.autoplay ? 1 : 0,
          start: Math.floor(props.resume),
          origin: window.location.origin,
          playsinline: 1,
        },
        events: {
          onReady: () => {
            timer = setInterval(save, 10000);
          },
          onStateChange: (event: any) => {
            if (event.data === 0) {
              save();
              emit("ended");
            }
            if (event.data === 2) save();
          },
          onError: () =>
            emit(
              "error",
              "Video tidak dapat diputar. YouTube dapat membatasi wilayah, akses video, atau izin penyematan. Lihat pesan pada player.",
            ),
        },
      });
    } catch {
      emit(
        "error",
        "Player YouTube tidak dapat dimuat. Periksa koneksi lalu coba lagi.",
      );
    }
  } else if (video.value) {
    if (props.source.provider === "hls" && Hls.isSupported()) {
      hls = new Hls();
      hls.loadSource(props.source.url);
      hls.attachMedia(video.value);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        qualities.value = hls!.levels.map((l, index) => ({
          height: l.height,
          index,
        }));
        if (props.autoplay) video.value?.play().catch(() => {});
      });
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal)
          emit(
            "error",
            "Stream tidak dapat diputar. Periksa URL, akses jaringan, dan izin CORS sumber.",
          );
      });
    } else video.value.src = props.source.url;
  }
});
function visibilitySave() {
  if (document.hidden) save();
}
onBeforeUnmount(() => {
  save();
  disposed = true;
  clearInterval(timer);
  hls?.destroy();
  yt?.destroy();
  window.removeEventListener("pagehide", save);
  document.removeEventListener("visibilitychange", visibilitySave);
});
</script>
<template>
  <div class="video-adapter" @keydown="keyboard">
    <div v-if="source.provider === 'youtube'" class="video-frame">
      <div ref="youtubeHost"></div>
    </div>
    <template v-else-if="source.provider === 'embed'">
      <!-- Zen hosts such as HD-1 reject sandboxed frames. Embed URLs are
           restricted to the Zen player origin by the backend. -->
      <div class="video-frame"><iframe :src="source.url" title="Zen episode player" allow="autoplay; fullscreen; picture-in-picture; encrypted-media" allowfullscreen></iframe></div>
      <p class="muted">Player Zen. Bahasa subtitle mengikuti server; progres otomatis belum didukung.</p>
    </template>
    <div v-else-if="source.provider === 'cloudflare'" class="video-frame">
      <iframe
        :src="`https://iframe.videodelivery.net/${source.url}`"
        title="Cloudflare Stream player"
        allow="
          accelerometer;
          gyroscope;
          autoplay;
          encrypted-media;
          picture-in-picture;
        "
        allowfullscreen
      ></iframe>
      <p class="muted">
        Player hosted. Penyimpanan progres belum didukung oleh adapter ini.
      </p>
    </div>
    <template v-else
      ><video
        ref="video"
        controls
        playsinline
        :autoplay="autoplay"
        crossorigin="anonymous"
        @loadedmetadata="metadata"
        @timeupdate="timeupdate"
        @pause="save"
        @ended="
          save();
          emit('ended');
        "
        @error="
          emit(
            'error',
            'Video tidak dapat diputar. Periksa URL, format, dan izin CORS sumber.',
          )
        "
      >
        <track
          v-for="s in source.subtitles"
          :key="s.url"
          kind="subtitles"
          :src="s.url"
          :srclang="s.language"
          :label="s.label"
        />
      </video>
      <div class="player-options">
        <label
          >Kecepatan<select v-model="rate" @change="speed">
            <option
              v-for="n in [0.5, 0.75, 1, 1.25, 1.5, 2]"
              :key="n"
              :value="n"
            >
              {{ n }}×
            </option>
          </select></label
        ><label v-if="qualities.length > 1"
          >Kualitas<select v-model="quality" @change="setQuality">
            <option :value="-1">Otomatis</option>
            <option v-for="q in qualities" :key="q.index" :value="q.index">
              {{ q.height }}p
            </option>
          </select></label
        ><span>Spasi: putar / jeda · ← →: 10 detik</span>
      </div></template
    >
  </div>
</template>

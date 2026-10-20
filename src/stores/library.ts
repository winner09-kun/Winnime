import { defineStore } from "pinia";
import { ref } from "vue";
import { api, errorMessage } from "../services/api";
import type {
  Anime,
  WatchEntry,
  WatchStatus,
  HistoryEntry,
  Settings,
} from "../types";
export const statuses: Record<WatchStatus, string> = {
  PLANNING: "Ingin ditonton",
  WATCHING: "Sedang ditonton",
  COMPLETED: "Selesai",
  PAUSED: "Ditunda",
  DROPPED: "Dihentikan",
};
export const useLibrary = defineStore("library", () => {
  const watchlist = ref<WatchEntry[]>([]),
    history = ref<HistoryEntry[]>([]),
    settings = ref<Settings>({
      autoplay: false,
      auto_next: false,
      show_completed: true,
    }),
    toast = ref(""),
    error = ref("");
  let timer: ReturnType<typeof setTimeout>;
  function notify(message: string) {
    toast.value = message;
    clearTimeout(timer);
    timer = setTimeout(() => (toast.value = ""), 4000);
  }
  async function load() {
    try {
      const [w, h, s] = await Promise.all([
        api.get("/watchlist"),
        api.get("/history"),
        api.get("/settings"),
      ]);
      watchlist.value = w.data;
      history.value = h.data;
      settings.value = s.data;
      error.value = "";
    } catch (e) {
      error.value = errorMessage(e);
    }
  }
  async function save(anime: Anime, status: WatchStatus = "PLANNING") {
    try {
      const { data } = await api.post("/watchlist", {
        anime_id: anime.id,
        anime,
        status,
      });
      watchlist.value = [
        data,
        ...watchlist.value.filter((x) => x.anime_id !== anime.id),
      ];
      notify("Watchlist diperbarui");
    } catch (e) {
      notify(errorMessage(e));
    }
  }
  async function remove(id: number) {
    try {
      await api.delete("/watchlist/" + id);
      watchlist.value = watchlist.value.filter((x) => x.anime_id !== id);
      notify("Anime dihapus dari watchlist");
    } catch (e) {
      notify(errorMessage(e));
    }
  }
  function has(id: number) {
    return watchlist.value.some((x) => x.anime_id === id);
  }
  async function progress(
    anime: Anime,
    episode: number,
    position: number,
    duration: number,
    completed = false,
  ) {
    const { data } = await api.post("/history", {
      anime_id: anime.id,
      episode,
      position,
      duration,
      completed: completed || (duration > 0 && position / duration >= 0.95),
      anime,
    });
    history.value = [
      data,
      ...history.value.filter((h) => h.episode_id !== data.episode_id),
    ];
  }
  async function reset(id?: string) {
    try {
      await api.delete(id ? "/history/" + id : "/history");
      history.value = id
        ? history.value.filter((h) => h.episode_id !== id)
        : [];
      notify("Riwayat diperbarui");
    } catch (e) {
      notify(errorMessage(e));
    }
  }
  return {
    watchlist,
    history,
    settings,
    toast,
    error,
    load,
    save,
    remove,
    has,
    notify,
    progress,
    reset,
  };
});

export interface Anime {
  id: number;
  mal_id?: number;
  title: string;
  titles: string[];
  cover?: string;
  banner?: string;
  description: string;
  score?: number;
  year?: number;
  season?: string;
  genres: string[];
  format?: string;
  status?: string;
  episodes?: number;
  duration?: number;
  studios: string[];
  links: { site: string; url: string }[];
  next_episode?: { episode: number; airingAt: number };
  characters: { name: string; image: string }[];
  relations: Anime[];
  recommendations: Anime[];
}
export type WatchStatus =
  "PLANNING" | "WATCHING" | "COMPLETED" | "PAUSED" | "DROPPED";
export interface WatchEntry {
  anime_id: number;
  anime: Anime;
  status: WatchStatus;
  updated_at: number;
}
export interface HistoryEntry {
  episode_id: string;
  anime_id: number;
  episode: number;
  position: number;
  duration: number;
  completed: boolean;
  anime: Anime;
  updated_at: number;
}
export interface Source {
  id: number;
  anime_id: number;
  episode: number;
  provider: "youtube" | "mp4" | "hls" | "cloudflare" | "embed";
  label?: string;
  url: string;
  language: string;
  subtitles: { url: string; language: string; label: string }[];
  available: boolean;
}
export interface Episode {
  number: number;
  title?: string;
  aired?: string;
  playable: boolean;
  configured?: boolean;
}
export interface Catalog {
  items: Anime[];
  has_next: boolean;
  stale?: boolean;
}
export interface Settings {
  autoplay: boolean;
  auto_next: boolean;
  show_completed: boolean;
}

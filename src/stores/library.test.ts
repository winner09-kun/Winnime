import { beforeEach, describe, it, expect, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useLibrary } from "./library";
import { api } from "../services/api";
import type { Anime } from "../types";
vi.mock("../services/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
  errorMessage: () => "Request failed",
}));
const anime = { id: 1, title: "Test fixture", genres: [] } as unknown as Anime;
describe("personal library", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });
  it("does not report success or mutate watchlist when saving fails", async () => {
    vi.mocked(api.post).mockRejectedValue(new Error());
    const store = useLibrary();
    await store.save(anime);
    expect(store.watchlist).toEqual([]);
    expect(store.toast).toBe("Request failed");
  });
  it("updates an existing watchlist entry without duplicates", async () => {
    const store = useLibrary();
    vi.mocked(api.post).mockResolvedValueOnce({
      data: { anime_id: 1, anime, status: "PLANNING" },
    });
    await store.save(anime);
    vi.mocked(api.post).mockResolvedValueOnce({
      data: { anime_id: 1, anime, status: "COMPLETED" },
    });
    await store.save(anime, "COMPLETED");
    expect(store.watchlist).toHaveLength(1);
    expect(store.watchlist[0]?.status).toBe("COMPLETED");
  });
  it("marks progress complete at 95 percent and retains episode identity", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { episode_id: "1:3", position: 96, duration: 100 },
    });
    const store = useLibrary();
    await store.progress(anime, 3, 96, 100);
    expect(api.post).toHaveBeenCalledWith(
      "/history",
      expect.objectContaining({ anime_id: 1, episode: 3, completed: true }),
    );
    expect(store.history[0]?.episode_id).toBe("1:3");
  });
  it("keeps saved history when deletion fails", async () => {
    const store = useLibrary();
    vi.mocked(api.post).mockResolvedValue({ data: { episode_id: "1:1" } });
    await store.progress(anime, 1, 0, 0);
    vi.mocked(api.delete).mockRejectedValue(new Error());
    await store.reset("1:1");
    expect(store.history).toHaveLength(1);
  });
});

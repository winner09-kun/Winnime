import axios from "axios";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 70000,
});
export function errorMessage(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => x.msg).join(". ");
    if (!e.response)
      return "Tidak dapat terhubung. Pastikan backend WINNIME berjalan, lalu coba lagi.";
  }
  return "Terjadi kesalahan. Silakan coba lagi.";
}

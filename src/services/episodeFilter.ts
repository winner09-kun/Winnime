export interface EpisodeFilterItem {
  number?: number;
  title?: string;
  episodeId?: string;
  playable?: boolean;
}

export function filterEpisodes<T extends EpisodeFilterItem>(items: T[], query: string, status = 'all', completedNumbers: number[] = []): T[] {
  const term = query.trim().toLocaleLowerCase();
  const numeric = /^\d+(?:\.\d+)?$/.test(term) ? Number(term) : undefined;
  const completed = new Set(completedNumbers);
  return items.filter(item => {
    // Provider slugs identify the episode independently of season numbers in the title.
    const match = item.episodeId?.match(/(?:^|-)episode-(\d+(?:\.\d+)?)(?:-|$)/i);
    const number = item.number ?? (match ? Number(match[1]) : undefined);
    const matches = !term || (numeric !== undefined
      ? number === numeric
      : `${item.title || ''} episode ${number ?? ''}`.toLocaleLowerCase().includes(term));
    if (!matches) return false;
    if (status === 'available') return item.playable === true;
    if (status === 'unavailable') return !item.playable;
    if (status === 'completed') return number !== undefined && completed.has(number);
    if (status === 'unwatched') return number === undefined || !completed.has(number);
    return true;
  });
}

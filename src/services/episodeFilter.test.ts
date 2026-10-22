import { describe, expect, it } from 'vitest';
import { filterEpisodes } from './episodeFilter';

describe('episode filtering', () => {
  const episodes = [{ number: 1, title: 'Awal perjalanan', playable: true }, { number: 10, title: 'Pertemuan', playable: false }];
  it('matches an exact episode number, including padded input', () => {
    expect(filterEpisodes(episodes, ' 01 ')).toEqual([episodes[0]]);
  });
  it('combines title and status and preserves source order', () => {
    expect(filterEpisodes(episodes, 'PERJALANAN', 'completed', [1])).toEqual([episodes[0]]);
    expect(filterEpisodes(episodes, '', 'unwatched', [1])).toEqual([episodes[1]]);
    expect(filterEpisodes(episodes, '', 'available')).toEqual([episodes[0]]);
    expect(filterEpisodes(episodes, '', 'unavailable')).toEqual([episodes[1]]);
    expect(filterEpisodes(episodes, 'missing')).toEqual([]);
    expect(filterEpisodes(episodes, '')).toEqual(episodes);
  });
  it('uses provider episode IDs without confusing season and episode numbers', () => {
    const streaming = [{ title: 'Anime Season 2 Episode 10', episodeId: 'anime-s2-episode-10-sub-indo' }];
    expect(filterEpisodes(streaming, '2')).toEqual([]);
    expect(filterEpisodes(streaming, '10')).toEqual(streaming);
  });
});

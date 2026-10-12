export function getNextSeasonNumber(seasons: readonly { season_number: number }[]): number {
  return seasons.reduce((max, season) => Math.max(max, season.season_number), 0) + 1
}

export function getNextEpisodeNumber(episodes: readonly { episode_number: number }[]): number {
  return episodes.reduce((max, episode) => Math.max(max, episode.episode_number), 0) + 1
}

export function isValidPositiveInteger(value: unknown): boolean {
  const number = typeof value === 'number' ? value : Number(value)
  return Number.isInteger(number) && number > 0
}

/** Presentation-only units. API coordinates, distance and collision remain integers in tiles. */
export const TILE = 48;
export const centreX = (x: number) => x * TILE + TILE / 2;
export const feetY = (y: number) => (y + 1) * TILE;

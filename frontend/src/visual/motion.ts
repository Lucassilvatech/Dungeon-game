import { direction, type Direction } from "./appearance";

export type Gait = {
  x: number;
  y: number;
  distance: number;
  dir: Direction;
  tick: number;
  moving: boolean;
};
export function createGait(x: number, y: number, dir: Direction = 0): Gait {
  return { x, y, distance: 0, dir, tick: 0, moving: false };
}

/** Finish each visible step before the next normal authoritative update. This
 * avoids accumulating lag/teleports on auto-routes while keeping single taps calm.
 */
export function synchronizedSpeed(distance: number, updateIntervalMs: number) {
  const duration = Math.min(300, Math.max(100, updateIntervalMs * 0.9));
  return (Math.max(1, distance) * 1000) / duration;
}
/** Walk phase follows actual interpolated distance. Clock, frame rate and reload
 * cannot make a stationary actor walk. Large state corrections reset the stride.
 */
export function advanceGait(
  gait: Gait,
  x: number,
  y: number,
  reduced = false,
): Gait {
  const dx = x - gait.x,
    dy = y - gait.y,
    travel = Math.hypot(dx, dy);
  const teleport = travel > 64;
  const moving = !teleport && travel > 0.01;
  const distance = teleport ? 0 : gait.distance + (moving ? travel : 0);
  return {
    x,
    y,
    distance,
    dir: moving ? direction(dx, dy, gait.dir) : gait.dir,
    tick: reduced ? 0 : Math.floor(distance / 5) % 8,
    moving,
  };
}

/** Constant speed; does not asymptotically slide toward the target like lerp. */
export function approach(
  x: number,
  y: number,
  tx: number,
  ty: number,
  deltaMs: number,
  speed = 156,
) {
  const dx = tx - x,
    dy = ty - y,
    distance = Math.hypot(dx, dy);
  if (distance > 128 || distance === 0) return { x: tx, y: ty };
  const travel = Math.min(
    distance,
    (speed * Math.max(0, Math.min(deltaMs, 100))) / 1000,
  );
  return { x: x + (dx / distance) * travel, y: y + (dy / distance) * travel };
}

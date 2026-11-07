import { TILE } from "./visual/scale";
import {
  createGait,
  advanceGait,
  approach,
  synchronizedSpeed,
  type Gait,
} from "./visual/motion";
import { useEffect, useRef } from "react";
import Phaser from "phaser";
import type { State, Enemy } from "./api";
import type { Peer, Target } from "./types";
import { createSprites, preloadSprites, frames } from "./sprites";
import {
  actorFrame,
  appearance,
  direction,
  type Direction,
} from "./visual/appearance";
import { hitBuildingEntrance } from "./visual/paths";
import { softwareRenderer } from "./visual/renderer";
import { Environment } from "./environment";
type Actor = {
  sprite: Phaser.GameObjects.Sprite;
  label: Phaser.GameObjects.Text;
  lastX: number;
  lastY: number;
  dying: boolean;
  boss: boolean;
  scale: number;
  dir: Direction;
};
export function Map({
  state,
  peers,
  onMove,
  onInteract,
  onTarget,
  fx,
}: {
  state: State;
  peers: Peer[];
  onMove: (dx: number, dy: number) => void;
  onInteract: () => void;
  onTarget: (t: Target) => void;
  fx: {
    seq: number;
    status: string;
    enemy_id?: number;
    damage?: number;
  } | null;
}) {
  const el = useRef<HTMLDivElement>(null),
    live = useRef({ state, peers, onMove, onInteract, onTarget, fx });
  live.current = { state, peers, onMove, onInteract, onTarget, fx };
  useEffect(() => {
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    class World extends Phaser.Scene {
      room = "";
      environment: Environment | null = null;
      heroDir: Direction = 0;
      lastMoveAt = 0;
      heroSpeed = 156;
      gaits = new WeakMap<Phaser.GameObjects.Sprite, Gait>();
      gait(sprite: Phaser.GameObjects.Sprite) {
        const before = this.gaits.get(sprite) ?? createGait(sprite.x, sprite.y);
        const next = advanceGait(before, sprite.x, sprite.y, motion.matches);
        this.gaits.set(sprite, next);
        return next;
      }
      lastDiagnostic = 0;
      preload() {
        preloadSprites(this);
      }
      hero!: Phaser.GameObjects.Sprite;
      back!: Phaser.GameObjects.Graphics;
      ambient!: Phaser.GameObjects.Graphics;
      actors = new globalThis.Map<number, Actor>();
      others = new globalThis.Map<number, Phaser.GameObjects.Sprite>();
      npcs: Phaser.GameObjects.Sprite[] = [];
      labels: Phaser.GameObjects.Text[] = [];
      lastTile = "";
      lastFx = 0;
      until = 0;
      effect = "";
      targetEnemy = 0;
      removed = new Set<number>();
      npcHomes: { x: number; y: number; walk: boolean }[] = [];
      recoveryLabel: Phaser.GameObjects.Text | null = null;
      label(x: number, y: number, text: string) {
        return this.add
          .text(x, y, text, {
            fontFamily: "monospace",
            fontSize: "10px",
            color: "#f5e6be",
            backgroundColor: "#10202bdd",
            padding: { x: 4, y: 3 },
          })
          .setOrigin(0.5)
          .setDepth(10000);
      }
      create() {
        createSprites(this);
        this.back = this.add.graphics();
        this.ambient = this.add.graphics().setDepth(1);
        this.hero = this.add
          .sprite(80, 80, "hero")
          .setOrigin(0.5, 1)
          .setDepth(15);
        this.input.keyboard?.on("keydown", (e: KeyboardEvent) => {
          if (
            e.repeat ||
            ["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(
              (e.target as HTMLElement)?.tagName,
            )
          )
            return;
          const d: Record<string, number[]> = {
            ArrowUp: [0, -1],
            w: [0, -1],
            ArrowDown: [0, 1],
            s: [0, 1],
            ArrowLeft: [-1, 0],
            a: [-1, 0],
            ArrowRight: [1, 0],
            d: [1, 0],
          };
          if (d[e.key]) {
            e.preventDefault();
            live.current.onMove(d[e.key][0], d[e.key][1]);
          }
          if (e.key === "e") live.current.onInteract();
        });
        this.input.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
          const p = this.cameras.main.getWorldPoint(pointer.x, pointer.y),
            x = Math.floor(p.x / TILE),
            y = Math.floor(p.y / TILE),
            s = live.current.state;
          const facade = hitBuildingEntrance(s, p.x, p.y);
          if (facade) {
            live.current.onTarget({
              x: facade.x,
              y: facade.y,
              kind: "exit",
              id: facade.exitId,
            });
            return;
          }
          // Visual body selection maps back to the existing authoritative actor tile.
          const bodyHit = (xx: number, yy: number) =>
            Math.abs(p.x - (xx * TILE + TILE / 2)) <= 16 &&
            p.y >= (yy + 1) * TILE - 62 &&
            p.y <= (yy + 1) * TILE;
          const serviceBody = s.map.service_npcs?.find((n) =>
            bodyHit(n.x, n.y),
          );
          if (serviceBody) {
            live.current.onTarget({
              x: serviceBody.x,
              y: serviceBody.y,
              kind: "service",
              serviceId: serviceBody.id,
            });
            return;
          }
          if (s.map.npc && bodyHit(s.map.npc[0], s.map.npc[1])) {
            live.current.onTarget({
              x: s.map.npc[0],
              y: s.map.npc[1],
              kind: "npc",
            });
            return;
          }
          const enemyBody = [...this.actors.entries()]
            .sort((a, b) => b[1].sprite.depth - a[1].sprite.depth)
            .find(
              ([id, a]) =>
                a.sprite.getBounds().contains(p.x, p.y) &&
                s.map.enemies.some((e) => e.id === id && e.state === "ALIVE"),
            );
          if (enemyBody) {
            const e = s.map.enemies.find((e) => e.id === enemyBody[0])!;
            live.current.onTarget({
              x: e.x,
              y: e.y,
              kind: "monster",
              monster: String(e.id),
            });
            return;
          }
          const lunarResource = s.map.lunar_resources?.find(
            (n) => n.x === x && n.y === y,
          );
          const resource = s.map.gather_nodes?.find(
            (n) => n.x === x && n.y === y && n.enabled && n.remaining > 0,
          );
          const service = s.map.service_npcs?.find(
            (n) => n.x === x && n.y === y,
          );
          const exit = s.room.exits.find((e) => e.x === x && e.y === y);
          const enemy = s.map.enemies.find(
              (e) => e.state === "ALIVE" && e.x === x && e.y === y,
            ),
            npc = s.map.npc;
          live.current.onTarget({
            x,
            y,
            kind: service
              ? "service"
              : exit
                ? "exit"
                : enemy
                  ? "monster"
                  : npc && npc[0] === x && npc[1] === y
                    ? "npc"
                    : lunarResource
                      ? "lunar"
                      : resource
                        ? "resource"
                        : "ground",
            id: exit?.id ?? lunarResource?.id ?? resource?.id,
            serviceId: service?.id,
            monster: enemy ? String(enemy.id) : undefined,
          });
        });
      }
      loadRoom(s: State) {
        this.room = s.room.id;
        this.back.clear();
        this.ambient.clear();
        this.actors.forEach((a) => {
          a.sprite.destroy();
          a.label.destroy();
        });
        this.actors.clear();
        this.others.forEach((a) => a.destroy());
        this.others.clear();
        this.npcs.forEach((a) => a.destroy());
        this.npcs = [];
        this.labels.forEach((a) => a.destroy());
        this.labels = [];
        this.npcHomes = [];
        this.recoveryLabel = null;
        this.removed.clear();
        this.tweens.killTweensOf(this.hero);
        this.environment?.destroy();
        this.environment = new Environment(this, s);
        el.current!.dataset.theme = this.environment.theme.id;
        if (s.map.npc) {
          const [x, y] = s.map.npc;
          this.npcs.push(
            this.add
              .sprite(
                x * TILE + TILE / 2,
                (y + 1) * TILE,
                s.map.npc_role === "recovery" ? "hooded" : "npc",
              )
              .setScale(1)
              .setOrigin(0.5, 1)
              .setDepth(12),
          );
          this.npcHomes.push({
            x: x * TILE + TILE / 2,
            y: (y + 1) * TILE,
            walk: false,
          });
          const caption = this.label(
            x * TILE + TILE / 2,
            (y + 1) * TILE - 62,
            "E · " + (s.map.npc_name ?? "Serviço da Guilda"),
          );
          if (s.map.npc_role === "recovery") {
            this.recoveryLabel = caption;
            caption.setVisible(false);
          } else this.recoveryLabel = null;
          this.labels.push(caption);
        }
        for (const n of s.map.service_npcs ?? []) {
          this.npcs.push(
            this.add
              .sprite(n.x * TILE + TILE / 2, (n.y + 1) * TILE, n.sprite)
              .setScale(1)
              .setOrigin(0.5, 1)
              .setDepth(12),
          );
          this.npcHomes.push({
            x: n.x * TILE + TILE / 2,
            y: (n.y + 1) * TILE,
            walk: false,
          });
          this.labels.push(
            this.label(n.x * TILE + TILE / 2, (n.y + 1) * TILE - 62, n.name),
          );
        }
        for (const n of s.map.npcs || []) {
          this.npcs.push(
            this.add
              .sprite(n.x * TILE + TILE / 2, (n.y + 1) * TILE, "peer")
              .setScale(1)
              .setOrigin(0.5, 1)
              .setDepth(11),
          );
          this.npcHomes.push({
            x: n.x * TILE + TILE / 2,
            y: (n.y + 1) * TILE,
            walk: n.walk,
          });
        }
        for (const e of s.room.exits)
          this.labels.push(
            this.label(
              e.x * TILE + TILE / 2,
              e.y * TILE - 45,
              e.known ? e.name : "? Caminho",
            ),
          );
        this.hero.setPosition(
          s.character.x * TILE + TILE / 2,
          (s.character.y + 1) * TILE,
        );
        this.gaits.set(
          this.hero,
          createGait(this.hero.x, this.hero.y, this.heroDir),
        );
        this.lastTile = `${s.character.x},${s.character.y}`;
        this.cameras.main
          .setBounds(0, 0, s.map.width * TILE, s.map.height * TILE)
          .setZoom(1)
          .startFollow(
            this.hero,
            true,
            1,
            1,
            0,
            Math.min(60, this.cameras.main.height * 0.1),
          );
        this.cameras.main.roundPixels = true;
        if (!motion.matches) this.cameras.main.fadeIn(160, 12, 23, 28);
      }
      createEnemy(e: Enemy) {
        const look = appearance(e, live.current.state);
        const bossFrame = (
          {
            moss_colossus: 0,
            thorn_chief: 1,
            abyssal_warden: 2,
            basalt_drake: 3,
          } as Record<string, number>
        )[look.key.replace("boss_", "")];
        const sprite = this.add
          .sprite(
            e.x * TILE + TILE / 2,
            (e.y + 1) * TILE,
            look.boss ? "bosses" : look.key,
            look.boss ? bossFrame : 0,
          )
          .setOrigin(0.5, 1)
          .setScale(look.scale)
          .setDepth(100 + (e.y + 1) * TILE);
        if (e.category === "rare") sprite.setTint(0xa8d8e7);
        const label = this.label(
          sprite.x,
          sprite.y - (look.boss ? 190 : look.scale > 1 ? 88 : 56),
          (e.category_label ?? "Comum") + " · " + e.name + " · " + e.level,
        ).setColor(e.name_color ?? "#e3eadb");
        this.actors.set(e.id, {
          sprite,
          label,
          lastX: e.x,
          lastY: e.y,
          dying: false,
          boss: look.boss,
          scale: look.scale,
          dir: 0,
        });
      }
      resourceKey = "";
      resourceLabels: Phaser.GameObjects.GameObject[] = [];
      update(time: number, delta: number) {
        if (!el.current) return;
        const { state: s, peers, fx } = live.current;
        if (this.room !== s.room.id) this.loadRoom(s);
        const resourceKey =
          s.room.id +
          JSON.stringify([s.map.gather_nodes, s.map.lunar_resources]);
        if (resourceKey !== this.resourceKey) {
          this.resourceKey = resourceKey;
          this.resourceLabels.forEach((o) => o.destroy());
          this.resourceLabels = [];
          for (const n of s.map.gather_nodes ?? []) {
            if (!n.enabled || !n.remaining) continue;
            this.resourceLabels.push(
              this.add
                .image(
                  n.x * TILE + TILE / 2,
                  (n.y + 1) * TILE - 2,
                  "effects",
                  n.definition === "herb"
                    ? frames.effects.herb
                    : frames.effects.ore,
                )
                .setScale(0.75)
                .setOrigin(0.5, 1)
                .setDepth(101 + n.y * TILE),
            );
            this.resourceLabels.push(
              this.label(
                n.x * TILE + TILE / 2,
                n.y * TILE - 14,
                n.name + " · " + n.remaining,
              ).setColor("#bfd39a"),
            );
          }
          for (const n of s.map.lunar_resources ?? []) {
            this.resourceLabels.push(
              this.add
                .image(
                  n.x * TILE + TILE / 2,
                  (n.y + 1) * TILE - 2,
                  "effects",
                  frames.effects.lunar,
                )
                .setScale(0.75)
                .setOrigin(0.5, 1)
                .setDepth(101 + n.y * TILE),
            );
            this.resourceLabels.push(
              this.label(
                n.x * TILE + TILE / 2,
                n.y * TILE - 14,
                BigInt(n.weight_mg) / 1000n + "g",
              ).setColor("#a9deff"),
            );
          }
        }
        const frame = Math.floor(time / 220) % 4;
        const c = s.character,
          key = `${c.x},${c.y}`;
        if (key !== this.lastTile) {
          this.heroDir = direction(
            c.x * TILE + TILE / 2 - this.hero.x,
            (c.y + 1) * TILE - this.hero.y,
            this.heroDir,
          );
          this.lastTile = key;
          const distance = Math.hypot(
            c.x * TILE + TILE / 2 - this.hero.x,
            (c.y + 1) * TILE - this.hero.y,
          );
          this.heroSpeed = synchronizedSpeed(distance, time - this.lastMoveAt);
          this.lastMoveAt = time;
        }
        const position = approach(
          this.hero.x,
          this.hero.y,
          c.x * TILE + TILE / 2,
          (c.y + 1) * TILE,
          delta,
          this.heroSpeed,
        );
        this.hero.setPosition(position.x, position.y);
        const heroGait = this.gait(this.hero);
        if (heroGait.moving) this.heroDir = heroGait.dir;
        if (fx && fx.seq !== this.lastFx) {
          this.lastFx = fx.seq;
          this.until = time + 650;
          this.effect = fx.status;
          this.targetEnemy = fx.enemy_id || 0;
          if (!motion.matches) this.cameras.main.shake(70, 0.0015);
          const actor = this.actors.get(fx.enemy_id ?? 0);
          if (actor && fx.damage) {
            const text = this.label(
              actor.sprite.x,
              actor.sprite.y - 44,
              "−" + fx.damage,
            );
            text.setColor("#ffdc91");
            this.tweens.add({
              targets: text,
              y: text.y - 20,
              alpha: 0,
              duration: 600,
              onComplete: () => text.destroy(),
            });
          }
        }
        const moving =
            Math.abs(this.hero.x - c.x * TILE - TILE / 2) +
              Math.abs(this.hero.y - (c.y + 1) * TILE) >
            1,
          active = time < this.until;
        this.hero
          .setFrame(
            actorFrame(
              active
                ? this.effect === "lost"
                  ? "death"
                  : this.until - time < 280
                    ? "hurt"
                    : "attack"
                : moving
                  ? "walk"
                  : "idle",
              this.heroDir,
              moving ? heroGait.tick : 0,
            ),
          )
          .setDepth(100 + this.hero.y);
        if (this.recoveryLabel && s.map.npc)
          this.recoveryLabel.setVisible(
            Math.abs(s.character.x - s.map.npc[0]) +
              Math.abs(s.character.y - s.map.npc[1]) <=
              4,
          );
        const ids = new Set(s.map.enemies.map((e) => e.id));
        this.actors.forEach((a, id) => {
          if (!ids.has(id)) {
            a.sprite.destroy();
            a.label.destroy();
            this.actors.delete(id);
          }
        });
        for (const e of s.map.enemies) {
          let a = this.actors.get(e.id);
          if (!a && e.state !== "DEAD" && !this.removed.has(e.id)) {
            this.createEnemy(e);
            a = this.actors.get(e.id);
          }
          if (!a) continue;
          if (e.state === "DEAD" || e.state === "DYING") {
            if (!a.dying) {
              a.dying = true;
              this.removed.add(e.id);
              a.label.destroy();
              this.tweens.killTweensOf(a.sprite);
              if (!a.boss) a.sprite.setFrame(actorFrame("hurt", a.dir, 0));
              this.time.delayedCall(140, () => {
                if (a!.sprite.active && !a!.boss)
                  a!.sprite.setFrame(actorFrame("death", a!.dir, 0));
              });
              this.tweens.add({
                targets: a.sprite,
                alpha: 0,
                y: a.sprite.y + 9,
                scaleY: 0.6,
                delay: 150,
                duration: 550,
                onComplete: () => {
                  a!.sprite.destroy();
                  this.actors.delete(e.id);
                },
              });
            }
            continue;
          }
          if (a.lastX !== e.x || a.lastY !== e.y) {
            a.dir = direction(e.x - a.lastX, e.y - a.lastY, a.dir);
            a.lastX = e.x;
            a.lastY = e.y;
          }
          const enemyPosition = approach(
            a.sprite.x,
            a.sprite.y,
            e.x * TILE + TILE / 2,
            (e.y + 1) * TILE,
            delta,
            80,
          );
          a.sprite.setPosition(enemyPosition.x, enemyPosition.y);
          const enemyGait = this.gait(a.sprite);
          if (enemyGait.moving) a.dir = enemyGait.dir;
          a.label.setPosition(
            Math.round(a.sprite.x),
            Math.round(a.sprite.y - (a.boss ? 190 : a.scale > 1 ? 88 : 56)),
          );
          a.sprite.setDepth(100 + a.sprite.y);
          const walking =
            Math.abs(a.sprite.x - e.x * TILE - TILE / 2) +
              Math.abs(a.sprite.y - (e.y + 1) * TILE) >
            1;
          if (!a.boss)
            a.sprite.setFrame(
              actorFrame(
                active && this.targetEnemy === e.id
                  ? "hurt"
                  : e.state === "IN_COMBAT"
                    ? "attack"
                    : walking
                      ? "walk"
                      : "idle",
                a.dir,
                walking ? enemyGait.tick : 0,
              ),
            );
          else {
            a.sprite.setAlpha(active && this.targetEnemy === e.id ? 0.65 : 1);
            if (!walking) a.sprite.y = (e.y + 1) * TILE;
          }
        }
        this.npcs.forEach((sp, i) => {
          const home = this.npcHomes[i];
          const cycle = (time + i * 137) % 8000;
          const walking = home.walk && cycle >= 4000;
          // Smooth out-and-back motion: zero offset at both walk/idle boundaries.
          const progress = Math.max(0, (cycle - 4000) / 4000);
          const offset = walking
            ? (progress <= 0.5 ? progress * 2 : (1 - progress) * 2) * 12
            : 0;
          sp.x = Math.round(home.x + offset);
          sp.y = home.y;
          const npcGait = this.gait(sp);
          sp.setFrame(
            actorFrame(
              npcGait.moving ? "walk" : "idle",
              npcGait.dir,
              npcGait.moving ? npcGait.tick : 0,
            ),
          ).setDepth(100 + sp.y);
        });
        const peerIds = new Set(peers.map((p) => p.id));
        this.others.forEach((sp, id) => {
          if (!peerIds.has(id)) {
            sp.destroy();
            this.others.delete(id);
          }
        });
        for (const p of peers) {
          let sp = this.others.get(p.id);
          if (!sp) {
            sp = this.add
              .sprite(p.x * TILE + TILE / 2, (p.y + 1) * TILE, "peer")
              .setScale(1)
              .setOrigin(0.5, 1)
              .setDepth(14);
            this.others.set(p.id, sp);
          }
          const walk =
            Math.abs(sp.x - p.x * TILE - TILE / 2) +
              Math.abs(sp.y - (p.y + 1) * TILE) >
            1;
          const peerPosition = approach(
            sp.x,
            sp.y,
            p.x * TILE + TILE / 2,
            (p.y + 1) * TILE,
            delta,
          );
          sp.setPosition(peerPosition.x, peerPosition.y);
          const peerGait = this.gait(sp);
          sp.setFrame(
            actorFrame(
              walk ? "walk" : "idle",
              peerGait.dir,
              walk ? peerGait.tick : 0,
            ),
          ).setDepth(100 + sp.y);
        }
        const g = this.ambient;
        g.clear();
        const selected = s.encounter?.selected_enemy_id ?? s.battle?.enemy_id;
        const target = selected ? this.actors.get(selected) : undefined;
        if (target) {
          g.lineStyle(2, 0xffd080, 0.95);
          g.strokeEllipse(target.sprite.x, target.sprite.y - 2, 30, 10);
        }
        g.fillStyle(0x142b2e, 0.32);
        g.fillEllipse(this.hero.x, this.hero.y - 2, 21, 6);
        for (const a of this.actors.values()) {
          if (a.dying) continue;
          g.fillEllipse(
            Math.round(a.sprite.x),
            Math.round(a.sprite.y - 2),
            a.boss ? 90 : 24,
            a.boss ? 18 : 6,
          );
        }
        for (const sp of [...this.npcs, ...this.others.values()])
          g.fillEllipse(Math.round(sp.x), Math.round(sp.y - 2), 22, 6);
        this.environment?.update(time, motion.matches, this.hero);
        if (
          time - this.lastDiagnostic > 1000 ||
          (moving && time - this.lastDiagnostic > 45)
        ) {
          this.lastDiagnostic = time;
          el.current!.dataset.visual = JSON.stringify({
            hero: {
              x: this.hero.x,
              y: this.hero.y,
              frame: this.hero.frame.name,
              dir: this.heroDir,
              moving,
            },
            theme: this.environment?.theme.id,
            room: s.room.id,
            renderer:
              this.game.renderer.type === Phaser.CANVAS ? "CANVAS" : "WEBGL",
            fps: Math.round(this.game.loop.actualFps),
            objects: this.children.length,
            lights: this.environment?.lights.length,
            particles: this.environment?.particles.length,
            placement: {
              count: this.environment?.plan.props.length,
              violations: this.environment?.plan.violations,
              rejected: this.environment?.plan.rejected,
            },
            tileSize: TILE,
            camera: {
              x: this.cameras.main.scrollX,
              y: this.cameras.main.scrollY,
              zoom: 1,
            },
            enemies: [...this.actors.entries()].map(([id, a]) => ({
              id,
              key: a.sprite.texture.key,
              frame: a.sprite.frame.name,
              scale: a.scale,
              boss: a.boss,
              hitbox: 32,
            })),
          });
        }
      }
    }
    const width = () =>
        Math.max(320, Math.floor(el.current!.clientWidth / 2) * 2),
      height = () =>
        Math.max(300, Math.floor(el.current!.clientHeight / 2) * 2);
    let renderer = Phaser.AUTO;
    const requested = new URLSearchParams(location.search).get("renderer");
    if (requested === "canvas") renderer = Phaser.CANVAS;
    else if (requested !== "webgl") {
      const probe = document.createElement("canvas"),
        gl = probe.getContext("webgl", {
          powerPreference: "high-performance",
          failIfMajorPerformanceCaveat: true,
        });
      if (!gl) renderer = Phaser.CANVAS;
      else {
        const info = gl.getExtension("WEBGL_debug_renderer_info");
        if (
          info &&
          softwareRenderer(
            String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)),
          )
        )
          renderer = Phaser.CANVAS;
        gl.getExtension("WEBGL_lose_context")?.loseContext();
      }
    }
    const game = new Phaser.Game({
      type: renderer,
      width: width(),
      height: height(),
      parent: el.current!,
      pixelArt: true,
      antialias: false,
      roundPixels: true,
      backgroundColor: "#273d3c",
      scene: World,
      banner: false,
      fps: { target: 60 },
      scale: { mode: Phaser.Scale.NONE },
    });
    const observer = new ResizeObserver(() => {
      if (game.isBooted) game.scale.resize(width(), height());
    });
    observer.observe(el.current!);
    return () => {
      observer.disconnect();
      game.destroy(true);
    };
  }, []);
  return (
    <div className="canvas" ref={el} aria-label="Mapa jogável da sala atual" />
  );
}

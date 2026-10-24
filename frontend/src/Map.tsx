import { useEffect, useRef } from "react";
import Phaser from "phaser";
import type { State, Enemy } from "./api";
import type { Peer, Target } from "./types";
import { createSprites } from "./sprites";
import { drawEnvironment } from "./environment";
type Actor = {
  sprite: Phaser.GameObjects.Sprite;
  label: Phaser.GameObjects.Text;
  lastX: number;
  lastY: number;
  dying: boolean;
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
  fx: { seq: number; status: string; enemy_id?: number } | null;
}) {
  const el = useRef<HTMLDivElement>(null),
    live = useRef({ state, peers, onMove, onInteract, onTarget, fx });
  live.current = { state, peers, onMove, onInteract, onTarget, fx };
  useEffect(() => {
    class World extends Phaser.Scene {
      room = "";
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
      label(x: number, y: number, text: string) {
        return this.add
          .text(x, y, text, {
            fontFamily: "monospace",
            fontSize: "9px",
            color: "#f5e6be",
            backgroundColor: "#1d3639bb",
            padding: { x: 4, y: 3 },
          })
          .setOrigin(0.5)
          .setDepth(100);
      }
      create() {
        createSprites(this);
        this.back = this.add.graphics();
        this.ambient = this.add.graphics().setDepth(1);
        this.hero = this.add.sprite(80, 80, "hero").setScale(1.5).setDepth(15);
        this.input.keyboard?.on("keydown", (e: KeyboardEvent) => {
          if (
            e.repeat ||
            ["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)
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
            x = Math.floor(p.x / 32),
            y = Math.floor(p.y / 32),
            s = live.current.state;
          const exit = s.room.exits.find((e) => e.x === x && e.y === y);
          const enemy = s.map.enemies.find(
              (e) => e.state === "ALIVE" && e.x === x && e.y === y,
            ),
            npc = s.map.npc;
          live.current.onTarget({
            x,
            y,
            kind: exit
              ? "exit"
              : enemy
                ? "monster"
                : npc && npc[0] === x && npc[1] === y
                  ? "npc"
                  : "ground",
            id: exit?.id,
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
        this.removed.clear();
        this.tweens.killTweensOf(this.hero);
        drawEnvironment(this.back, s);
        if (s.map.npc) {
          const [x, y] = s.map.npc;
          this.npcs.push(
            this.add
              .sprite(x * 32 + 16, y * 32 + 12, "npc")
              .setScale(1.5)
              .setDepth(12),
          );
          this.npcHomes.push({ x: x * 32 + 16, y: y * 32 + 12, walk: false });
          this.labels.push(
            this.label(x * 32 + 16, y * 32 - 17, "E · Recepcionista"),
          );
        }
        for (const n of s.map.npcs || []) {
          this.npcs.push(
            this.add
              .sprite(n.x * 32 + 16, n.y * 32 + 12, "peer")
              .setScale(1.5)
              .setDepth(11),
          );
          this.npcHomes.push({
            x: n.x * 32 + 16,
            y: n.y * 32 + 12,
            walk: n.walk,
          });
        }
        for (const e of s.room.exits) {
          this.back.fillStyle(0x24363a);
          this.back.fillRect(e.x * 32 + 3, e.y * 32, 26, 32);
          this.back.lineStyle(3, 0xc0a36f);
          this.back.strokeRect(e.x * 32 + 2, e.y * 32 - 4, 28, 36);
          this.labels.push(
            this.label(
              e.x * 32 + 16,
              e.y * 32 - 15,
              e.known ? e.name : "? Caminho",
            ),
          );
        }
        this.hero.setPosition(s.character.x * 32 + 16, s.character.y * 32 + 12);
        this.lastTile = `${s.character.x},${s.character.y}`;
        this.cameras.main
          .setBounds(0, 0, s.map.width * 32, s.map.height * 32)
          .setZoom(1)
          .startFollow(this.hero, true, 0.12, 0.12);
        this.cameras.main.fadeIn(200, 20, 32, 34);
      }
      createEnemy(e: Enemy) {
        const sprite = this.add
          .sprite(e.x * 32 + 16, e.y * 32 + 12, e.species)
          .setScale(1.5)
          .setDepth(12);
        const label = this.label(
          sprite.x,
          sprite.y - 27,
          e.name + " · " + e.level,
        );
        this.actors.set(e.id, {
          sprite,
          label,
          lastX: e.x,
          lastY: e.y,
          dying: false,
        });
      }
      update(time: number) {
        const { state: s, peers, fx } = live.current;
        if (this.room !== s.room.id) this.loadRoom(s);
        const frame = Math.floor(time / 220) % 4;
        const c = s.character,
          key = `${c.x},${c.y}`;
        if (key !== this.lastTile) {
          this.lastTile = key;
          this.tweens.add({
            targets: this.hero,
            x: c.x * 32 + 16,
            y: c.y * 32 + 12,
            duration: 145,
            ease: "Sine.easeOut",
          });
        }
        if (fx && fx.seq !== this.lastFx) {
          this.lastFx = fx.seq;
          this.until = time + 650;
          this.effect = fx.status;
          this.targetEnemy = fx.enemy_id || 0;
          this.cameras.main.shake(70, 0.0015);
        }
        const moving =
            Math.abs(this.hero.x - c.x * 32 - 16) +
              Math.abs(this.hero.y - c.y * 32 - 12) >
            1,
          active = time < this.until;
        this.hero.setFrame(
          (active
            ? this.effect === "lost"
              ? 4
              : this.until - time < 280
                ? 3
                : 2
            : moving
              ? 1
              : 0) *
            4 +
            (moving ? Math.floor(time / 90) % 4 : frame),
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
              a.sprite.setFrame(12);
              this.time.delayedCall(140, () => {
                if (a!.sprite.active) a!.sprite.setFrame(16);
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
            a.lastX = e.x;
            a.lastY = e.y;
            this.tweens.add({
              targets: a.sprite,
              x: e.x * 32 + 16,
              y: e.y * 32 + 12,
              duration: 600,
              ease: "Sine.easeInOut",
            });
          }
          a.label.setPosition(a.sprite.x, a.sprite.y - 27);
          const walking =
            Math.abs(a.sprite.x - e.x * 32 - 16) +
              Math.abs(a.sprite.y - e.y * 32 - 12) >
            1;
          a.sprite.setFrame(
            (active && this.targetEnemy === e.id
              ? 3
              : e.state === "IN_COMBAT"
                ? 2
                : walking
                  ? 1
                  : 0) *
              4 +
              frame,
          );
        }
        this.npcs.forEach((sp, i) => {
          const home = this.npcHomes[i];
          const walking = home.walk && Math.floor(time / 4000) % 2 === 1;
          const offset = walking
            ? Math.sin(((time % 4000) / 4000) * Math.PI) * 26
            : 0;
          sp.x = home.x + offset;
          sp.setFrame((walking ? 1 : 0) * 4 + frame);
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
              .sprite(p.x * 32 + 16, p.y * 32 + 12, "peer")
              .setScale(1.5)
              .setDepth(14);
            this.others.set(p.id, sp);
          }
          const walk =
            Math.abs(sp.x - p.x * 32 - 16) + Math.abs(sp.y - p.y * 32 - 12) > 1;
          sp.x = Phaser.Math.Linear(sp.x, p.x * 32 + 16, 0.2);
          sp.y = Phaser.Math.Linear(sp.y, p.y * 32 + 12, 0.2);
          sp.setFrame((walk ? 4 : 0) + frame);
        }
        const g = this.ambient;
        g.clear();
        g.fillStyle(0x142b2e, 0.25);
        g.fillEllipse(this.hero.x, this.hero.y + 17, 21, 8);
        const fires = (s.map.decorations || [])
          .filter((d) => d.kind === "torch")
          .slice(0, 12);
        for (const d of fires) {
          const x = d.x * 32 + 16,
            y = d.y * 32 + 8;
          g.fillStyle(0xffc46d, 0.07);
          g.fillCircle(x, y, 24 + Math.sin(time / 180 + d.x) * 3);
          g.fillStyle(0xf5b959);
          g.fillRect(x - 4, y - 9 + Math.sin(time / 100) * 2, 7, 12);
          g.fillStyle(0xffe3a0);
          g.fillRect(x - 2, y - 4, 3, 6);
        }
        for (let i = 0; i < 10; i++) {
          g.fillStyle(0xe8d597, 0.3 + Math.sin(time / 600 + i) * 0.15);
          g.fillRect(
            (i * 113 + time / 90) % (s.map.width * 32),
            (i * 91 + Math.sin(time / 1500 + i) * 12) % (s.map.height * 32),
            2,
            2,
          );
        }
      }
    }
    const game = new Phaser.Game({
      type: Phaser.AUTO,
      width: 960,
      height: 544,
      parent: el.current!,
      pixelArt: true,
      roundPixels: true,
      backgroundColor: "#273d3c",
      scene: World,
      banner: false,
      fps: { target: 30 },
      scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    });
    return () => game.destroy(true);
  }, []);
  return (
    <div className="canvas" ref={el} aria-label="Mapa jogável da sala atual" />
  );
}

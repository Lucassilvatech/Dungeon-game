import { useEffect, useRef } from "react";
import Phaser from "phaser";
import type { State } from "./api";
import type { Peer, Target } from "./types";
import { createSprites } from "./sprites";
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
  onTarget: (target: Target) => void;
  fx: { seq: number; status: string } | null;
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
      entities = new globalThis.Map<string, Phaser.GameObjects.Sprite>();
      names: Phaser.GameObjects.Text[] = [];
      remote = new globalThis.Map<number, Phaser.GameObjects.Sprite>();
      lastFx = 0;
      effectUntil = 0;
      effectStatus = "";
      lastTile = "";
      create() {
        createSprites(this);
        this.back = this.add.graphics();
        this.ambient = this.add.graphics().setDepth(1);
        this.hero = this.add.sprite(80, 80, "hero").setScale(2).setDepth(10);
        this.input.keyboard?.on("keydown", (e: KeyboardEvent) => {
          if (
            e.repeat ||
            ["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)
          )
            return;
          const dirs: Record<string, number[]> = {
            ArrowUp: [0, -1],
            w: [0, -1],
            ArrowDown: [0, 1],
            s: [0, 1],
            ArrowLeft: [-1, 0],
            a: [-1, 0],
            ArrowRight: [1, 0],
            d: [1, 0],
          };
          if (dirs[e.key]) {
            e.preventDefault();
            live.current.onMove(dirs[e.key][0], dirs[e.key][1]);
          }
          if (e.key === "e") live.current.onInteract();
        });
        this.input.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
          const p = this.cameras.main.getWorldPoint(pointer.x, pointer.y);
          const x = Math.floor(p.x / 32),
            y = Math.floor(p.y / 32);
          const s = live.current.state;
          const exit = s.room.exits.find((e) => e.x === x && e.y === y);
          const monster = Object.entries(s.map.monsters).find(
            ([, p]) => p[0] === x && p[1] === y,
          );
          const npc = s.map.npc;
          live.current.onTarget({
            x,
            y,
            kind: exit
              ? "exit"
              : monster
                ? "monster"
                : npc && npc[0] === x && npc[1] === y
                  ? "npc"
                  : "ground",
            id: exit?.id,
            monster: monster?.[0],
          });
        });
      }
      loadRoom(s: State) {
        this.room = s.room.id;
        this.back.clear();
        this.ambient.clear();
        this.entities.forEach((v) => v.destroy());
        this.entities.clear();
        this.remote.forEach((v) => v.destroy());
        this.remote.clear();
        this.names.forEach((v) => v.destroy());
        this.names = [];
        this.tweens.killTweensOf(this.hero);
        const g = this.back,
          m = s.map,
          interior = m.theme === "interior",
          city = m.theme === "city";
        for (let y = 0; y < m.height; y++)
          for (let x = 0; x < m.width; x++) {
            const path = city && (Math.abs(x - 10) < 2 || Math.abs(y - 10) < 2);
            g.fillStyle(
              interior
                ? (x + y) % 2
                  ? 0x76604c
                  : 0x7f6851
                : path
                  ? 0xafa58a
                  : (x + y) % 2
                    ? 0x56745b
                    : 0x527057,
            );
            g.fillRect(x * 32, y * 32, 32, 32);
            if (!interior && !path) {
              g.fillStyle(0x7e9569);
              g.fillRect(x * 32 + 6, y * 32 + 9, 2, 3);
              if ((x * 7 + y * 3) % 13 === 0) {
                g.fillStyle(0xe5be81);
                g.fillRect(x * 32 + 20, y * 32 + 18, 3, 3);
              }
            } else {
              g.lineStyle(1, interior ? 0x594b40 : 0x8b8d77, 0.4);
              g.strokeRect(x * 32 + 1, y * 32 + 1, 30, 30);
            }
          }
        m.walls.forEach(([x, y]) => {
          g.fillStyle(interior ? 0x443d3b : 0x304d48);
          g.fillRect(x * 32, y * 32, 32, 32);
          g.fillStyle(interior ? 0x95806a : 0x6b8274);
          g.fillRect(x * 32 + 2, y * 32 + 3, 28, 20);
          g.fillStyle(0xb3ad8c, 0.3);
          g.fillRect(x * 32 + 2, y * 32 + 3, 28, 3);
        });
        m.buildings?.forEach((b) => {
          g.fillStyle(0x343e40, 0.35);
          g.fillRect(b.x * 32 + 7, b.y * 32 + 10, b.width * 32, b.height * 32);
          g.fillStyle(0xbca37c);
          g.fillRect(b.x * 32, b.y * 32, b.width * 32, b.height * 32);
          g.fillStyle(0x734e51);
          g.fillRect(b.x * 32 - 5, b.y * 32 - 8, b.width * 32 + 10, 72);
          for (let y = 0; y < 4; y++) {
            g.lineStyle(2, 0x986568);
            g.lineBetween(
              b.x * 32 - 4,
              b.y * 32 + y * 16,
              b.x * 32 + b.width * 32 + 4,
              b.y * 32 + y * 16,
            );
          }
          for (let x = 1; x < b.width - 1; x += 2) {
            g.fillStyle(0x674c42);
            g.fillRect((b.x + x) * 32, (b.y + 3) * 32, 18, 20);
            g.fillStyle(0xf2ce86);
            g.fillRect((b.x + x) * 32 + 3, (b.y + 3) * 32 + 3, 12, 14);
          }
          this.label(b.x * 32 + b.width * 16, b.y * 32 + 74, b.name);
        });
        if (interior) {
          g.fillStyle(0x5a7e78);
          g.fillRect(2 * 32, 4 * 32, 4 * 32, 5 * 32);
          g.lineStyle(2, 0xbca77c);
          g.strokeRect(2 * 32 + 5, 4 * 32 + 5, 4 * 32 - 10, 5 * 32 - 10);
          g.fillStyle(0x4e3e37);
          g.fillRect(9 * 32, 2 * 32, 4 * 32, 32);
          g.fillStyle(0xc3aa79);
          g.fillRect(9 * 32 + 5, 2 * 32 + 4, 4 * 32 - 10, 22);
          if (s.room.kind === "GUILD") {
            this.label(11 * 32, 2 * 32 - 8, "Quadro da Guilda");
            g.fillStyle(0xe2d0a0);
            for (let i = 0; i < 4; i++)
              g.fillRect((9 + i) * 32 + 9, 2 * 32 + 8, 12, 13);
          } else {
            this.label(11 * 32, 2 * 32 - 8, "Área de prática");
            g.lineStyle(2, 0xb49b71, 0.5);
            g.strokeCircle(10 * 32 + 16, 6 * 32 + 16, 58);
          }
        }
        // Bounded decorative trees and lanterns; no hidden entities from other rooms.
        if (!interior)
          for (const [x, y] of [
            [3, 7],
            [12, 1],
            [1, 5],
            [m.width - 3, m.height - 3],
          ]) {
            if (m.walls.some((p) => p[0] === x && p[1] === y)) continue;
            g.fillStyle(0x334d40, 0.4);
            g.fillEllipse(x * 32 + 20, y * 32 + 24, 46, 18);
            g.fillStyle(0x796048);
            g.fillRect(x * 32 + 12, y * 32 + 3, 8, 27);
            g.fillStyle(0x355e4b);
            g.fillRect(x * 32 - 1, y * 32 - 20, 34, 28);
            g.fillStyle(0x638265);
            g.fillRect(x * 32 + 3, y * 32 - 26, 24, 18);
          }
        if (m.npc) {
          this.spawn("npc", "npc", m.npc);
          this.label(m.npc[0] * 32 + 16, m.npc[1] * 32 - 23, "E · Curandeira");
        }
        Object.entries(m.monsters).forEach(([id, p]) => {
          this.spawn(id, id, p);
          this.label(p[0] * 32 + 16, p[1] * 32 - 24, m.enemy_names?.[id] || id);
        });
        for (const exit of s.room.exits) {
          g.fillStyle(0x273e40);
          g.fillRect(exit.x * 32 + 2, exit.y * 32, 28, 32);
          g.fillStyle(0xd3b274);
          g.fillRect(exit.x * 32 + 5, exit.y * 32 + 3, 22, 5);
          this.label(
            exit.x * 32 + 16,
            exit.y * 32 - 14,
            exit.known ? exit.name : "? Caminho",
          );
        }
        this.hero.setPosition(s.character.x * 32 + 16, s.character.y * 32 + 14);
        this.lastTile = `${s.character.x},${s.character.y}`;
        this.cameras.main
          .setBounds(0, 0, m.width * 32, m.height * 32)
          .setZoom(1.3)
          .startFollow(this.hero, true, 0.12, 0.12);
        this.cameras.main.fadeIn(220, 16, 26, 30);
      }
      label(x: number, y: number, text: string) {
        this.names.push(
          this.add
            .text(x, y, text, {
              fontFamily: "monospace",
              fontSize: "10px",
              color: "#f6e3b3",
              backgroundColor: "#243b3caa",
              padding: { x: 4, y: 3 },
            })
            .setOrigin(0.5)
            .setDepth(20),
        );
      }
      spawn(id: string, key: string, p: number[]) {
        const sprite = this.add
          .sprite(p[0] * 32 + 16, p[1] * 32 + 14, key)
          .setScale(2)
          .setDepth(7);
        this.entities.set(id, sprite);
      }
      update(time: number) {
        const { state: s, peers, fx } = live.current;
        if (this.room !== s.room.id) this.loadRoom(s);
        const c = s.character,
          tile = `${c.x},${c.y}`;
        if (tile !== this.lastTile) {
          this.lastTile = tile;
          this.tweens.add({
            targets: this.hero,
            x: c.x * 32 + 16,
            y: c.y * 32 + 14,
            duration: 145,
            ease: "Sine.easeOut",
          });
        }
        if (fx && fx.seq !== this.lastFx) {
          this.lastFx = fx.seq;
          this.effectUntil = time + 750;
          this.effectStatus = fx.status;
          this.cameras.main.shake(90, 0.002);
        }
        const moving =
          Math.abs(this.hero.x - (c.x * 32 + 16)) +
            Math.abs(this.hero.y - (c.y * 32 + 14)) >
          1;
        const activeFx = time < this.effectUntil;
        const frame = Math.floor(time / (moving ? 100 : 240)) % 4;
        this.hero.setFrame(
          (activeFx
            ? this.effectStatus === "lost"
              ? 4
              : this.effectUntil - time < 400
                ? 3
                : 2
            : moving
              ? 1
              : 0) *
            4 +
            frame,
        );
        this.entities.forEach((sprite, id) => {
          const death = activeFx && this.effectStatus === "won";
          sprite.setFrame((activeFx ? (death ? 4 : 3) : 0) * 4 + frame);
          sprite.setAlpha(death ? 0.5 : 1);
          if (s.battle && s.battle.monster === id && !activeFx)
            sprite.setFrame(8 + frame);
        });
        const ids = new Set(peers.map((p) => p.id));
        this.remote.forEach((sp, id) => {
          if (!ids.has(id)) {
            sp.destroy();
            this.remote.delete(id);
          }
        });
        for (const p of peers) {
          let sp = this.remote.get(p.id);
          if (!sp) {
            sp = this.add
              .sprite(p.x * 32 + 16, p.y * 32 + 14, "peer")
              .setScale(2)
              .setDepth(9);
            this.remote.set(p.id, sp);
          }
          const moving =
            Math.abs(sp.x - (p.x * 32 + 16)) > 1 ||
            Math.abs(sp.y - (p.y * 32 + 14)) > 1;
          sp.x = Phaser.Math.Linear(sp.x, p.x * 32 + 16, 0.18);
          sp.y = Phaser.Math.Linear(sp.y, p.y * 32 + 14, 0.18);
          sp.setFrame((moving ? 4 : 0) + frame);
        }
        const g = this.ambient;
        g.clear();
        g.fillStyle(0x172f32, 0.25);
        g.fillEllipse(this.hero.x, this.hero.y + 22, 26, 10);
        // At most 8 motes and two small fire glows, all local to this room.
        for (const [x, y] of [
          [2, 4],
          [s.map.width - 3, 4],
        ]) {
          g.fillStyle(0xf4bc6b, 0.06);
          g.fillCircle(x * 32 + 16, y * 32, 30 + Math.sin(time / 190) * 3);
          g.fillStyle(0xb57a46);
          g.fillRect(x * 32 + 13, y * 32, 5, 13);
          g.fillStyle(0xffd986);
          g.fillRect(x * 32 + 12, y * 32 - 8 + Math.sin(time / 120) * 2, 7, 10);
          g.fillStyle(0xffedb0);
          g.fillRect(x * 32 + 14, y * 32 - 5, 3, 5);
        }
        for (let i = 0; i < 8; i++) {
          const x = (i * 83 + time / 80) % (s.map.width * 32),
            y = (i * 61 + Math.sin(time / 1500 + i) * 14) % (s.map.height * 32);
          g.fillStyle(0xf1dc9a, 0.3 + Math.sin(time / 700 + i) * 0.2);
          g.fillRect(x, y, 2, 2);
        }
        if (s.map.portal) {
          const [x, y] = s.map.portal;
          g.lineStyle(2, 0x9cd8d0, 0.6);
          g.strokeEllipse(
            x * 32 + 16,
            y * 32 + 12,
            22 + Math.sin(time / 240) * 4,
            30,
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
      backgroundColor: "#243d3d",
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

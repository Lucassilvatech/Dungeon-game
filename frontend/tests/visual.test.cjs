const { test } = require("node:test"),
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path"),
  ts = require("typescript"),
  Module = require("node:module");
const cache = {};
function load(file) {
  if (file.endsWith(".json"))
    return JSON.parse(
      fs.readFileSync(path.resolve(__dirname, "../src/visual", file), "utf8"),
    );
  file = path.resolve(__dirname, "../src/visual", file + ".ts");
  if (cache[file]) return cache[file].exports;
  const m = new Module(file, module);
  cache[file] = m;
  m.filename = file;
  m.paths = module.paths;
  const original = m.require.bind(m);
  m.require = (id) =>
    id.startsWith(".")
      ? load(
          path.relative(
            path.resolve(__dirname, "../src/visual"),
            path.resolve(path.dirname(file), id),
          ),
        )
      : original(id);
  m._compile(
    ts.transpileModule(fs.readFileSync(file, "utf8"), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        esModuleInterop: true,
        target: ts.ScriptTarget.ES2022,
      },
    }).outputText,
    file,
  );
  return m.exports;
}
const { resolveTheme, tileHash, THEMES } = load("themes"),
  { appearance, actorFrame, direction } = load("appearance"),
  { placementMask, canPlace } = load("placement");
const state = (kind = "PROCEDURAL", theme = "moss_stone") => ({
  room: { id: "test-room", kind, exits: [{ x: 28, y: 12 }] },
  map: {
    width: 32,
    height: 24,
    seed: 158,
    walls: [],
    monsters: { slime: [8, 8] },
    npc: [10, 5],
    service_npcs: [{ x: 20, y: 5 }],
    portal: [25, 10],
    gather_nodes: [{ x: 20, y: 18 }],
    lunar_resources: [{ x: 23, y: 18 }],
    theme,
  },
});
for (const [k, theme] of Object.entries({
  CITY: "SAFE_VILLAGE",
  GUILD: "SAFE_GUILD",
  TRAINING: "SAFE_GUILD",
  BUILDING_INTERIOR: "SAFE_GUILD",
  BOSS: "BOSS_RITUAL",
  SECRET_DUNGEON: "SECRET_DUNGEON",
}))
  test("real room " + k + " resolves " + theme, () =>
    assert.equal(resolveTheme(state(k)).id, theme),
  );
test("all legacy environmental profiles have distinct authored ground", () => {
  assert.deepEqual(
    ["moss_stone", "wild_ruins", "crystal_bones", "abandoned_wood"].map(
      (k) => resolveTheme(state("PROCEDURAL", k)).groundSet,
    ),
    ["moss", "ruins", "cave", "crypt"],
  );
});
test("bosses have independent artwork, size and fixed tile hitbox", () => {
  const s = state();
  for (const species of ["boss", "warden", "champion"]) {
    const b = appearance({ species, spawn_key: "key", category: "boss" }, s),
      common = appearance(
        { species: "slime", spawn_key: "key", category: "common" },
        s,
      );
    assert.notEqual(b.key, common.key);
    assert(b.width * b.scale > common.width * common.scale * 2);
    assert.equal(b.hitbox, 32);
  }
});
test("fixed boss identities do not vary by seed", () => {
  for (const species of ["boss", "warden"]) {
    const a = appearance({ species, spawn_key: "x" }, state());
    const b = state();
    b.map.seed = 999;
    assert.equal(a.key, appearance({ species, spawn_key: "x" }, b).key);
  }
});
test("procedural boss reloads use identical appearance", () => {
  const s = state(),
    e = { species: "champion", spawn_key: "guardian:2", category: "boss" };
  assert.deepEqual(
    appearance(e, s),
    appearance(e, JSON.parse(JSON.stringify(s))),
  );
});
test("miniboss uses independent elite sprite and stays smaller than boss", () => {
  const e = { species: "goblin", spawn_key: "x" };
  const mini = appearance({ ...e, category: "miniboss" }, state()),
    boss = appearance({ ...e, species: "champion", category: "boss" }, state());
  assert.equal(mini.key, "goblin_elite");
  assert.equal(mini.boss, false);
  assert(mini.height * mini.scale < boss.height * boss.scale);
});
test("spawn door exit portal NPC resource and required paths are reserved", () => {
  const s = state(),
    mask = placementMask(s);
  for (const [x, y] of [
    [2, 2],
    [28, 12],
    [10, 5],
    [20, 5],
    [25, 10],
    [20, 18],
    [23, 18],
    [8, 8],
  ])
    assert(
      !canPlace({ kind: "tree", x, y, width: 1, height: 1 }, mask, 32, 24),
    );
  assert(
    !canPlace({ kind: "tree", x: 1, y: 1, width: 3, height: 4 }, mask, 32, 24),
  );
  assert(mask.has("3,2"));
});
test("complete prop footprint must clear every reserved tile", () => {
  assert(
    !canPlace(
      { kind: "tree", x: 5, y: 5, width: 3, height: 4 },
      new Set(["7,8"]),
      32,
      24,
    ),
  );
  assert(
    canPlace(
      { kind: "tree", x: 5, y: 5, width: 3, height: 4 },
      new Set(["8,8"]),
      32,
      24,
    ),
  );
});
test("village paths and arena centers are never decorated by tall props", () => {
  const mask = placementMask(state("CITY"));
  assert(mask.has("10,20"));
  assert(mask.has("25,18"));
  for (const k of ["BOSS", "SECRET_DUNGEON"])
    assert(placementMask(state(k)).has("15,12"));
});
test("tile detail is repeatable and varied", () => {
  const a = Array.from({ length: 100 }, (_, i) => tileHash(88, i, 7) % 8);
  assert.deepEqual(
    a,
    Array.from({ length: 100 }, (_, i) => tileHash(88, i, 7) % 8),
  );
  assert(new Set(a).size >= 6);
});
test("all directional idle/walk/action/death frames are valid", () => {
  const all = new Set();
  for (const mode of ["idle", "walk", "attack", "hurt", "death"])
    for (let dir = 0; dir < 4; dir++)
      for (let f = 0; f < (mode === "walk" ? 8 : 4); f++)
        all.add(actorFrame(mode, dir, f));
  assert.equal(all.size, 96);
  assert.equal(Math.max(...all), 95);
  assert.equal(direction(0, -1), 3);
  assert.equal(direction(-1, 0), 1);
});
test("every shipped atlas matches its recorded checksum and total PNG payload stays under 450KB", () => {
  const crypto = require("node:crypto"),
    root = path.resolve(__dirname, "../public/assets/pixel"),
    manifest = require(root + "/manifest.json");
  let bytes = 0;
  for (const v of Object.values(manifest)) {
    const buf = fs.readFileSync(root + "/" + v.file);
    bytes += buf.length;
    assert.equal(
      crypto.createHash("sha256").update(buf).digest("hex"),
      v.sha256,
    );
  }
  assert(bytes < 450000);
});

const { cityPaths, buildingEntrances } = load("paths");
test("building paths meet exact entry tile and route around occupied facades", () => {
  const s = state("CITY");
  s.map.width = 52;
  s.map.height = 36;
  s.map.buildings = [
    { x: 7, y: 3, width: 6, height: 4 },
    { x: 35, y: 24, width: 6, height: 5 },
  ];
  s.room.exits = [{ id: 3, x: 9, y: 7 }];
  for (const b of s.map.buildings)
    for (let y = b.y; y < b.y + b.height; y++)
      for (let x = b.x; x < b.x + b.width; x++) s.map.walls.push([x, y]);
  const roads = cityPaths(s),
    doors = buildingEntrances(s);
  assert.deepEqual(
    doors.map((d) => [d.x, d.y]),
    [
      [9, 7],
      [37, 29],
    ],
  );
  assert.equal(doors[0].exitId, 3);
  for (const d of doors) assert(roads.has(d.x + "," + d.y));
  for (const p of s.map.walls) assert(!roads.has(p.join(",")));
  const queue = ["37,29"],
    seen = new Set(queue);
  for (let i = 0; i < queue.length; i++) {
    const [x, y] = queue[i].split(",").map(Number);
    for (const [dx, dy] of [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ]) {
      const k = x + dx + "," + (y + dy);
      if (roads.has(k) && !seen.has(k)) {
        seen.add(k);
        queue.push(k);
      }
    }
  }
  assert(seen.has("9,7"));
  assert(placementMask(s).has("37,29"));
});

test("wandering enemies do not reroll reserved decoration routes", () => {
  const s = state();
  s.map.spawns = { slime: { x: 8, y: 8, species: "slime" } };
  const a = [...placementMask(s)].sort();
  s.map.monsters.slime = [15, 15];
  assert.deepEqual([...placementMask(s)].sort(), a);
});

const { softwareRenderer } = load("renderer");
test("software GPU uses lightweight Canvas; real GPUs keep WebGL", () => {
  for (const gpu of [
    "ANGLE SwiftShader driver",
    "llvmpipe",
    "Microsoft Basic Render",
  ])
    assert(softwareRenderer(gpu));
  for (const gpu of ["NVIDIA GeForce RTX", "Intel Iris Xe", "AMD Radeon"])
    assert(!softwareRenderer(gpu));
});

const { hitBuildingEntrance } = load("paths");
test("painted facade click resolves exactly to authorized exit; decorative doors do not travel", () => {
  const s = state("CITY");
  s.map.buildings = [
    { x: 7, y: 3, width: 6, height: 4 },
    { x: 22, y: 5, width: 7, height: 5 },
  ];
  s.room.exits = [{ id: 44, x: 9, y: 7 }];
  assert.equal(hitBuildingEntrance(s, centreX(9), 7 * TILE - 19).exitId, 44);
  assert.equal(hitBuildingEntrance(s, centreX(26), 10 * TILE - 20), undefined);
  assert.equal(hitBuildingEntrance(s, centreX(11), 5 * TILE), undefined);
});

const { buildZones, planScenery, placementViolations } = load("placement");
test("every decoration footprint in every theme avoids all forbidden zones", () => {
  for (const kind of [
    "CITY",
    "GUILD",
    "TRAINING",
    "BUILDING_INTERIOR",
    "COMMON",
    "COMBAT",
    "PROCEDURAL",
    "BOSS",
    "SECRET_DUNGEON",
  ])
    for (let seed = 0; seed < 30; seed++) {
      const s = state(kind);
      s.room.safe = ["CITY", "GUILD"].includes(kind);
      s.map.seed = seed;
      const plan = planScenery(s);
      assert.deepEqual(plan.violations, []);
      for (const p of plan.props) {
        assert.deepEqual(placementViolations(p.footprint, plan.zones), []);
        assert([...plan.zones.DECORATION_ALLOWED].length > 0);
      }
    }
});
test("legacy props on roads doors buildings NPCs and resources never bypass validation", () => {
  const s = state("CITY");
  s.map.decorations = [
    { kind: "crate", x: 10, y: 18, solid: true },
    { kind: "barrel", x: 10, y: 5, solid: true },
    { kind: "well", x: 20, y: 5 },
    { kind: "flower", x: 20, y: 18 },
    { kind: "rock", x: 2, y: 2 },
  ];
  const p = planScenery(s);
  assert.deepEqual(p.violations, []);
  for (const d of p.props)
    assert(!s.map.decorations.some((old) => old.x === d.x && old.y === d.y));
});
test("reference based character atlases have larger frames and 96 animation cells including eight walking poses", () => {
  const manifest = require("../src/visual/atlas.json");
  for (const name of [
    "hero",
    "merchant",
    "alchemist",
    "blacksmith",
    "npc",
    "peer",
    "hooded",
    "goblin",
  ])
    assert.deepEqual(manifest[name].frames, {
      frameWidth: 48,
      frameHeight: 64,
      endFrame: 95,
    });
});

test("interior furniture requires a deliberate footprint or contextual seating/wall", () => {
  const s = state("GUILD");
  s.map.decorations = [
    { kind: "table", x: 6, y: 14, width: 3, height: 2 },
    { kind: "chair", x: 7, y: 13 },
    { kind: "chair", x: 19, y: 19 },
    { kind: "shelf", x: 19, y: 19 },
    { kind: "banner", x: 19, y: 18 },
  ];
  const p = planScenery(s);
  assert(p.fixtures.some((d) => d.kind === "table"));
  assert(p.fixtures.some((d) => d.kind === "chair" && d.x === 7));
  assert(!p.fixtures.some((d) => d.x === 19));
});

test("a rejected table never leaves an orphan decorative chair", () => {
  const s = state("GUILD");
  s.map.decorations = [
    { kind: "table", x: 6, y: 14, width: 3, height: 2 },
    { kind: "chair", x: 7, y: 13 },
  ];
  s.map.lunar_resources = [{ x: 7, y: 16 }];
  const p = planScenery(s);
  assert(!p.fixtures.some((d) => d.kind === "table"));
  assert(!p.fixtures.some((d) => d.kind === "chair"));
});

test("full wall fixture bounds exclude door approach, NPCs and resources", () => {
  const { wallMounts } = load("composition"),
    s = state("COMMON");
  s.map.walls = Array.from({ length: s.map.width }, (_, x) => [x, 0]);
  s.room.exits = [{ x: 5, y: 1 }];
  s.map.lunar_resources = [{ x: 13, y: 1 }];
  const zones = buildZones(s),
    mounts = wallMounts(s.map.width, zones);
  assert(mounts.length > 0);
  for (const m of mounts)
    for (const k of m.cells)
      for (const n of [
        "PATH",
        "DOOR_ACCESS",
        "NPC_ZONE",
        "INTERACTION_ZONE",
        "RESOURCE_ZONE",
        "SPAWN_ZONE",
        "COMBAT_ZONE",
        "BUILDING_FOOTPRINT",
      ])
        assert(!zones[n].has(k));
});

test("village never regenerates rejected crate, barrel, well, rock and station props", () => {
  const s = state("CITY");
  for (let seed = 0; seed < 12; seed++) {
    s.map.seed = seed;
    const plan = planScenery(s);
    assert.deepEqual(plan.violations, []);
    assert(
      !plan.props.some((p) =>
        ["well", "barrel", "crate", "rock", "alchemy", "forge"].includes(
          p.kind,
        ),
      ),
    );
  }
});

test("tree bounds derive from actual art and never cover paths", () => {
  const s = state("CITY");
  s.room.safe = true;
  const { planScenery, placementViolations, visualFootprint } =
    load("placement");
  const planned = planScenery(s);
  assert.deepEqual(visualFootprint({ kind: "tree", x: 12, y: 12 }), {
    kind: "tree",
    x: 11,
    y: 9,
    width: 3,
    height: 4,
  });
  for (const p of planned.props.filter((p) => p.kind === "tree")) {
    assert.equal(p.footprint.width, 3);
    assert.equal(p.footprint.height, 4);
    assert.deepEqual(placementViolations(p.footprint, planned.zones), []);
  }
  assert.deepEqual(planned.violations, []);
});

const { mapModel } = load("model"),
  { TILE, centreX, feetY } = load("scale");
const { createGait, advanceGait, approach } = load("motion");
test("continuous authoritative auto-route steps do not accumulate visual lag", () => {
  const { synchronizedSpeed } = load("motion");
  let x = 0;
  for (let tile = 1; tile <= 30; tile++) {
    const target = tile * TILE,
      speed = synchronizedSpeed(target - x, 160);
    for (let frame = 0; frame < 10; frame++)
      x = approach(x, 0, target, 0, 16, speed).x;
    assert(Math.abs(x - target) < 0.001);
  }
});
test("new visual model preserves every logical coordinate and separates physical obstacles", () => {
  const s = state("CITY");
  s.map.buildings = [{ x: 7, y: 3, width: 6, height: 4 }];
  s.map.walls = [
    [0, 0],
    [3, 3],
    [7, 3],
    [8, 3],
    [20, 14],
    [21, 14],
  ];
  const original = JSON.stringify(s),
    m = mapModel(s);
  assert.equal(JSON.stringify(s), original);
  assert.deepEqual(m.obstacles, [[3, 3]]);
  assert.deepEqual(m.boundary, [[0, 0]]);
  assert.deepEqual(m.masonry, [
    [20, 14],
    [21, 14],
  ]);
  assert(m.buildingCells.has("7,3"));
  assert.equal(centreX(9), 9 * TILE + TILE / 2);
  assert.equal(feetY(7), 8 * TILE);
});
test("three reference families select new continuous materials", () => {
  for (const [room, ground] of [
    ["CITY", "grass"],
    ["COMMON", "ruins"],
    ["PROCEDURAL", "ruins"],
    ["BOSS", "ritual"],
    ["SECRET_DUNGEON", "ritual"],
    ["GUILD", "wood"],
  ])
    assert.equal(mapModel(state(room)).ground, ground);
});
test("walking follows distance equally at different frame rates and stops without sliding", () => {
  for (const fps of [30, 60, 120]) {
    let gait = createGait(0, 0),
      position = { x: 0, y: 0 };
    for (let i = 0; i < fps; i++) {
      position = approach(position.x, position.y, 100, 0, 1000 / fps, 100);
      gait = advanceGait(gait, position.x, position.y);
    }
    assert(Math.abs(position.x - 100) < 0.00001);
    assert.equal(gait.dir, 2);
    assert.equal(Math.round(gait.distance), 100);
    const stopped = advanceGait(gait, 100, 0);
    assert.equal(stopped.moving, false);
    assert(Math.abs(stopped.distance - gait.distance) < 0.00001);
  }
});
test("teleport/reload and reduced motion do not synthesize walking distance", () => {
  let gait = advanceGait(createGait(80, 80), 84, 80);
  const stopped = advanceGait(gait, 84, 80);
  assert.equal(stopped.distance, 4);
  assert.equal(stopped.moving, false);
  gait = advanceGait(gait, 800, 800);
  assert.equal(gait.distance, 0);
  assert.equal(gait.moving, false);
  assert.equal(advanceGait(gait, 805, 800, true).tick, 0);
});
test("new source and shipping map assets have reproducible checksums within 1MB", () => {
  const crypto = require("node:crypto"),
    manifest = require("../src/visual/map-atlas.json");
  let bytes = 0;
  for (const [name, entry] of Object.entries(manifest.files)) {
    const data = fs.readFileSync(
      path.resolve(__dirname, "../public/assets/maps", name),
    );
    assert.equal(data.length, entry.bytes);
    assert.equal(
      crypto.createHash("sha256").update(data).digest("hex"),
      entry.sha256,
    );
    bytes += data.length;
  }
  assert(bytes < 1000000);
  assert(Object.keys(manifest.assets).length >= 40);
});
test("authored rendered tree bounds fit inside exactly the reserved cells", () => {
  const manifest = require("../src/visual/map-atlas.json");
  const { visualFootprint } = load("placement");
  const p = { kind: "tree", x: 14, y: 14 },
    f = visualFootprint(p);
  for (const name of ["tree_1", "tree_2", "tree_3"]) {
    const a = manifest.assets[name],
      x = centreX(p.x),
      y = feetY(p.y);
    assert(x - a.width / 2 >= f.x * TILE);
    assert(x + a.width / 2 <= (f.x + f.width) * TILE);
    assert(y - a.height >= f.y * TILE);
    assert(y <= (f.y + f.height) * TILE);
  }
});

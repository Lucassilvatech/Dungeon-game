const fs = require("fs"),
  path = require("path"),
  assert = require("node:assert/strict"),
  ts = require("typescript"),
  Module = require("module"),
  cache = {};
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
  m.require = (id) =>
    load(
      path.relative(
        path.resolve(__dirname, "../src/visual"),
        path.resolve(path.dirname(file), id),
      ),
    );
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
const fixtures = JSON.parse(
    fs.readFileSync(
      process.env.VISUAL_LAYOUT_FIXTURES || "/tmp/visual-layouts.json",
    ),
  ),
  placement = load("placement"),
  paths = load("paths");
let props = 0;
const counts = {};
for (const s of fixtures) {
  const p = placement.planScenery(s);
  assert.deepEqual(p.violations, []);
  const blocked = new Set(s.map.walls.map((p) => p.join(","))),
    road = paths.cityPaths(s);
  counts[s.room.kind] = (counts[s.room.kind] || 0) + 1;
  props += p.props.length;
  // Independently enumerate every cell in the actual visible prop footprint.
  for (const d of p.props)
    for (let y = d.footprint.y; y < d.footprint.y + d.footprint.height; y++)
      for (let x = d.footprint.x; x < d.footprint.x + d.footprint.width; x++) {
        const k = x + "," + y;
        assert(!blocked.has(k));
        assert(!road.has(k));
        for (const n of [
          "BUILDING_FOOTPRINT",
          "DOOR_ACCESS",
          "NPC_ZONE",
          "INTERACTION_ZONE",
          "SPAWN_ZONE",
          "RESOURCE_ZONE",
          "COMBAT_ZONE",
        ])
          assert(
            !p.zones[n].has(k),
            JSON.stringify({
              kind: s.room.kind,
              seed: s.map.seed,
              prop: d.kind,
              x,
              y,
              zone: n,
            }),
          );
      }
  if (s.room.kind === "CITY") {
    assert(
      p.props.filter((p) => p.kind === "tree").length >= 4,
      "village must retain groves, not become empty",
    );
    assert(p.props.filter((p) => p.kind === "well").length <= 1);
    for (const d of paths.buildingEntrances(s)) {
      assert(road.has(d.x + "," + d.y), "path meets doorstep");
      const queue = [[d.x, d.y]],
        seen = new Set(queue.map((p) => p.join(",")));
      let connected = false;
      for (let i = 0; i < queue.length; i++) {
        const [x, y] = queue[i];
        if (paths.isVillagePath(x, y)) connected = true;
        for (const [dx, dy] of [
          [1, 0],
          [-1, 0],
          [0, 1],
          [0, -1],
        ]) {
          const a = x + dx,
            b = y + dy,
            k = a + "," + b;
          if (road.has(k) && !seen.has(k)) {
            seen.add(k);
            queue.push([a, b]);
          }
        }
      }
      assert(connected);
      assert(!blocked.has(d.x + "," + d.y));
    }
  }
}
const result = {
  status: "PASS",
  layouts: fixtures.length,
  room_types: counts,
  props_audited: props,
  forbidden_intersections: 0,
  paths_connect_building_doors: true,
};
if (process.env.VISUAL_AUDIT_OUTPUT)
  fs.writeFileSync(
    process.env.VISUAL_AUDIT_OUTPUT,
    JSON.stringify(result, null, 2) + "\n",
  );
console.log(JSON.stringify(result));

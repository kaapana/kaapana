#!/usr/bin/env node
// Generated with Claude (claude.ai/claude-code)
//
// Fix dcmjs TrackingIdentifier constructor bug (fixed upstream in dcmjs v0.50.2, PR #494).
//
// Root cause: Babel compiles `super(options)` in a class that extends Array to:
//   _callSuper(this, TrackingIdentifier, [options])
// This passes options as an element to the underlying Array constructor, making
// the Template length wrong (3 instead of 2). _MeasurementsAndQualitativeEvaluations
// then throws: "Option 'trackingIdentifier' must include..."
//
// The fix: change [options] -> [] so no extra elements are inserted.
//
// Searches ALL dcmjs installations under /src/node_modules (including nested
// copies inside dicom-microscopy-viewer or other packages) because webpack may
// resolve dcmjs from a nested location rather than the top-level package.
const fs = require("fs");
const path = require("path");

// The Babel-compiled super(options) call for TrackingIdentifier
const PATTERN = /_callSuper\(this,\s*TrackingIdentifier,\s*\[(\w+)\]\)/;

function findAllDcmjsDirs(nmDir) {
  const results = [];
  if (!fs.existsSync(nmDir)) return results;
  for (const entry of fs.readdirSync(nmDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const full = path.join(nmDir, entry.name);
    if (entry.name === "dcmjs") {
      results.push(full);
      // don't recurse into dcmjs's own node_modules
    } else {
      const nested = path.join(full, "node_modules");
      if (fs.existsSync(nested)) {
        results.push(...findAllDcmjsDirs(nested));
      }
    }
  }
  return results;
}

function findJsFiles(dir) {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== "node_modules") {
      results.push(...findJsFiles(full));
    } else if (entry.isFile() && entry.name.endsWith(".js")) {
      results.push(full);
    }
  }
  return results;
}

const rootNodeModules = "/src/node_modules";
const dcmjsDirs = findAllDcmjsDirs(rootNodeModules);
console.log(`Found ${dcmjsDirs.length} dcmjs installation(s):`);
for (const d of dcmjsDirs) {
  const pkgJson = path.join(d, "package.json");
  const version = fs.existsSync(pkgJson)
    ? JSON.parse(fs.readFileSync(pkgJson, "utf8")).version
    : "unknown";
  console.log(`  ${d} (v${version})`);
}

let patched = false;

for (const dcmjsDir of dcmjsDirs) {
  const allFiles = findJsFiles(dcmjsDir);
  console.log(`\nScanning ${allFiles.length} JS files in ${dcmjsDir}`);

  for (const fp of allFiles) {
    const content = fs.readFileSync(fp, "utf8");
    const match = PATTERN.exec(content);
    if (!match) continue;

    const paramName = match[1];
    console.log(`  Found _callSuper(this, TrackingIdentifier, [${paramName}]) in: ${fp}`);

    const fixed = content.replace(
      PATTERN,
      `_callSuper(this, TrackingIdentifier, [])`
    );

    fs.writeFileSync(fp, fixed);
    console.log(`  -> Patched [${paramName}] -> [] in ${fp}`);
    patched = true;
  }
}

if (!patched) {
  console.warn(
    "dcmjs patch not applied — _callSuper(this, TrackingIdentifier, [X]) not found in any installation. " +
    "May already be fixed or build format changed."
  );
}

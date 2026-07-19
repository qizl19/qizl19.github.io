import fs from "node:fs";
import path from "node:path";

const [sourcePath, outputPath] = process.argv.slice(2);
if (!sourcePath || !outputPath) {
  console.error("Usage: node tools/import_aircraft_data.mjs <aircraft.ts> <aircraft.json>");
  process.exit(2);
}

const source = fs.readFileSync(sourcePath, "utf8");
const marker = "export const aircraftProfiles: AircraftProfile[] =";
const start = source.indexOf(marker);
const end = source.indexOf("\n];", start);
if (start < 0 || end < 0) {
  throw new Error("Unable to locate aircraftProfiles in the TypeScript source");
}

const arraySource = source.slice(start + marker.length, end + 2).trim();
const profiles = Function(`"use strict"; return (${arraySource});`)();

for (const profile of profiles) {
  profile.heroImage = `/aircraft/assets${profile.heroImage}`;
  profile.pdf = `/aircraft/assets/pdf/${path.basename(profile.pdf)}`;
  for (const photo of profile.photos) {
    photo.src = `/aircraft/assets${photo.src}`;
  }
}

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, `${JSON.stringify(profiles, null, 2)}\n`, "utf8");
console.log(`Imported ${profiles.length} aircraft profiles to ${outputPath}`);

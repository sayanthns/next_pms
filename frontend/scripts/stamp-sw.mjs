// Postbuild: stamp the service worker cache names with the freshly-built bundle
// hash so every deploy produces a new SW → it self-purges old caches on activate.
// Without this, the SW serves stale bundles and frontend deploys appear to "not work".
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const indexHtml = resolve(here, '../../next_pms/public/frontend/index.html')
const swPath = resolve(here, '../../next_pms/public/js/sw.js')

const html = readFileSync(indexHtml, 'utf8')
const m = html.match(/index-([A-Za-z0-9_-]+)\.js/)
const ver = m ? m[1] : 'nohash'

let sw = readFileSync(swPath, 'utf8')
sw = sw.replace(/const CACHE_NAME = '[^']*';/, "const CACHE_NAME = 'next-pms-shell-" + ver + "';")
sw = sw.replace(/const ASSETS_CACHE = '[^']*';/, "const ASSETS_CACHE = 'next-pms-assets-" + ver + "';")
writeFileSync(swPath, sw)
console.log('[stamp-sw] cache version =', ver)

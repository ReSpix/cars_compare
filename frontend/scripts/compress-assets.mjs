import { readdir, readFile, writeFile } from 'node:fs/promises'
import { gzipSync } from 'node:zlib'

const assets = new URL('../dist/assets/', import.meta.url)
const files = await readdir(assets)
await Promise.all(files.filter((file) => /\.(css|js)$/.test(file)).map(async (file) => {
  const content = await readFile(new URL(file, assets))
  await writeFile(new URL(`${file}.gz`, assets), gzipSync(content, { level: 9 }))
}))

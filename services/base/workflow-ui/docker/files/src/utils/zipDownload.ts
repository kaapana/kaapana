// CRC-32 lookup table, computed once at module load
const CRC_TABLE = (() => {
  const t = new Uint32Array(256)
  for (let n = 0; n < 256; n++) {
    let c = n
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1)
    t[n] = c
  }
  return t
})()

function crc32(data: Uint8Array): number {
  let c = 0xffffffff
  for (const b of data) c = (c >>> 8) ^ CRC_TABLE[(c ^ b) & 0xff]
  return (c ^ 0xffffffff) >>> 0
}

export interface ZipEntry {
  name: string
  content: string
}

export function downloadAsZip(zipName: string, entries: ZipEntry[]): void {
  const enc = new TextEncoder()
  const now = new Date()
  const dosTime = ((now.getHours() << 11) | (now.getMinutes() << 5) | Math.floor(now.getSeconds() / 2)) & 0xffff
  const dosDate = ((((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate())) & 0xffff

  const pieces: Uint8Array[] = []
  type CdEntry = { name: Uint8Array; crc: number; size: number; localOffset: number }
  const cdEntries: CdEntry[] = []
  let localPos = 0

  for (const entry of entries) {
    const data = enc.encode(entry.content)
    const name = enc.encode(entry.name)
    const crc  = crc32(data)
    const size = data.length

    const lh = new Uint8Array(30)
    const dv = new DataView(lh.buffer)
    dv.setUint32(0,  0x04034b50, true) // local file header signature
    dv.setUint16(4,  20,         true) // version needed
    dv.setUint16(6,  0,          true) // flags
    dv.setUint16(8,  0,          true) // compression (stored = 0)
    dv.setUint16(10, dosTime,    true)
    dv.setUint16(12, dosDate,    true)
    dv.setUint32(14, crc,        true)
    dv.setUint32(18, size,       true) // compressed size
    dv.setUint32(22, size,       true) // uncompressed size
    dv.setUint16(26, name.length,true)
    dv.setUint16(28, 0,          true) // extra field length

    cdEntries.push({ name, crc, size, localOffset: localPos })
    localPos += 30 + name.length + size
    pieces.push(lh, name, data)
  }

  // Central directory
  const cdStart = localPos
  for (const cd of cdEntries) {
    const cde = new Uint8Array(46)
    const dv  = new DataView(cde.buffer)
    dv.setUint32(0,  0x02014b50,    true) // central dir signature
    dv.setUint16(4,  20,            true) // version made by
    dv.setUint16(6,  20,            true) // version needed
    dv.setUint16(8,  0,             true) // flags
    dv.setUint16(10, 0,             true) // compression
    dv.setUint16(12, dosTime,       true)
    dv.setUint16(14, dosDate,       true)
    dv.setUint32(16, cd.crc,        true)
    dv.setUint32(20, cd.size,       true) // compressed size
    dv.setUint32(24, cd.size,       true) // uncompressed size
    dv.setUint16(28, cd.name.length,true)
    dv.setUint16(30, 0,             true) // extra length
    dv.setUint16(32, 0,             true) // comment length
    dv.setUint16(34, 0,             true) // disk start
    dv.setUint16(36, 0,             true) // internal attributes
    dv.setUint32(38, 0,             true) // external attributes
    dv.setUint32(42, cd.localOffset,true) // local header offset
    localPos += 46 + cd.name.length
    pieces.push(cde, cd.name)
  }

  // End of central directory record
  const cdSize = localPos - cdStart
  const eocd   = new Uint8Array(22)
  const edv    = new DataView(eocd.buffer)
  edv.setUint32(0,  0x06054b50,     true) // EOCD signature
  edv.setUint16(4,  0,              true) // disk number
  edv.setUint16(6,  0,              true) // start disk
  edv.setUint16(8,  entries.length, true) // entries on this disk
  edv.setUint16(10, entries.length, true) // total entries
  edv.setUint32(12, cdSize,         true) // central dir size
  edv.setUint32(16, cdStart,        true) // central dir offset
  edv.setUint16(20, 0,              true) // comment length
  pieces.push(eocd)

  // Concatenate all pieces into one Uint8Array
  const total = pieces.reduce((s, p) => s + p.length, 0)
  const zip   = new Uint8Array(total)
  let offset  = 0
  for (const p of pieces) { zip.set(p, offset); offset += p.length }

  const blob = new Blob([zip], { type: 'application/zip' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = zipName
  a.click()
  URL.revokeObjectURL(url)
}

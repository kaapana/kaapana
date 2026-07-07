import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

const LONG_VRS = new Set(['OB', 'OD', 'OF', 'OL', 'OW', 'SQ', 'UC', 'UN', 'UR', 'UT']);

function isLongVr(vr: string): boolean {
  return LONG_VRS.has(vr);
}

function encodeTag(group: number, element: number, vr: string, value: Buffer): Buffer {
  const tag = Buffer.alloc(4);
  tag.writeUInt16LE(group, 0);
  tag.writeUInt16LE(element, 2);
  const vrBytes = Buffer.from(vr, 'ascii');
  if (isLongVr(vr)) {
    const reserved = Buffer.alloc(2);
    const length = Buffer.alloc(4);
    length.writeUInt32LE(value.length, 0);
    return Buffer.concat([tag, vrBytes, reserved, length, value]);
  } else {
    const length = Buffer.alloc(2);
    length.writeUInt16LE(value.length, 0);
    return Buffer.concat([tag, vrBytes, length, value]);
  }
}

function paddedStr(value: string, length?: number): Buffer {
  const buf = Buffer.from(value, 'ascii');
  if (length && buf.length < length) {
    return Buffer.concat([buf, Buffer.alloc(length - buf.length, 0x20)]);
  }
  if (buf.length % 2 !== 0) {
    return Buffer.concat([buf, Buffer.alloc(1, 0x20)]);
  }
  return buf;
}

function createMinimalDicom(seriesInstanceUID: string, studyInstanceUID: string, sopInstanceUID: string): Buffer {
  const parts: Buffer[] = [];
  parts.push(Buffer.alloc(128));
  parts.push(Buffer.from('DICM', 'ascii'));

  const sopClassUid = paddedStr('1.2.840.10008.5.1.4.1.1.2', 28);
  const sopInstanceUid = paddedStr(sopInstanceUID);
  const tsUid = paddedStr('1.2.840.10008.1.2.1', 26);

  const metaParts: Buffer[] = [];
  metaParts.push(encodeTag(0x0002, 0x0001, 'OB', Buffer.from([0x00, 0x01])));
  metaParts.push(encodeTag(0x0002, 0x0010, 'UI', tsUid));
  metaParts.push(encodeTag(0x0002, 0x0002, 'UI', Buffer.from(sopClassUid)));
  metaParts.push(encodeTag(0x0002, 0x0003, 'UI', Buffer.from(sopInstanceUid)));

  const metaBody = Buffer.concat(metaParts);
  const groupLen = Buffer.alloc(4);
  groupLen.writeUInt32LE(metaBody.length, 0);
  parts.push(encodeTag(0x0002, 0x0000, 'UL', groupLen));
  parts.push(metaBody);

  const rows = 16;
  const cols = 16;
  const pixelCount = rows * cols;

  const dsParts: Buffer[] = [];
  dsParts.push(encodeTag(0x0008, 0x0016, 'UI', Buffer.from(sopClassUid)));
  dsParts.push(encodeTag(0x0008, 0x0018, 'UI', Buffer.from(sopInstanceUid)));
  dsParts.push(encodeTag(0x0008, 0x0060, 'CS', paddedStr('CT')));

  const pn = Buffer.concat([Buffer.from('Test^Patient', 'ascii'), Buffer.alloc(2, 0x20)]);
  dsParts.push(encodeTag(0x0010, 0x0010, 'PN', pn));
  dsParts.push(encodeTag(0x0010, 0x0020, 'LO', paddedStr('TEST001')));

  const studyUid = paddedStr(studyInstanceUID);
  dsParts.push(encodeTag(0x0020, 0x000D, 'UI', Buffer.from(studyUid)));
  const seriesUid = paddedStr(seriesInstanceUID);
  dsParts.push(encodeTag(0x0020, 0x000E, 'UI', Buffer.from(seriesUid)));
  dsParts.push(encodeTag(0x0020, 0x0011, 'IS', paddedStr('1')));
  dsParts.push(encodeTag(0x0020, 0x0013, 'IS', paddedStr('1')));

  dsParts.push(encodeTag(0x0028, 0x0002, 'US', u16le(1)));
  dsParts.push(encodeTag(0x0028, 0x0004, 'CS', paddedStr('MONOCHROME2')));
  dsParts.push(encodeTag(0x0028, 0x0010, 'US', u16le(rows)));
  dsParts.push(encodeTag(0x0028, 0x0011, 'US', u16le(cols)));
  dsParts.push(encodeTag(0x0028, 0x0100, 'US', u16le(16)));
  dsParts.push(encodeTag(0x0028, 0x0101, 'US', u16le(16)));
  dsParts.push(encodeTag(0x0028, 0x0102, 'US', u16le(15)));
  dsParts.push(encodeTag(0x0028, 0x0103, 'US', u16le(0)));
  dsParts.push(encodeTag(0x0028, 0x1050, 'DS', paddedStr('500')));
  dsParts.push(encodeTag(0x0028, 0x1051, 'DS', paddedStr('1200')));
  dsParts.push(encodeTag(0x0028, 0x1052, 'DS', paddedStr('0')));
  dsParts.push(encodeTag(0x0028, 0x1053, 'DS', paddedStr('1')));

  dsParts.push(encodeTag(0x0018, 0x0060, 'DS', paddedStr('120')));

  // 16x16 circle: center (7.5, 7.5), radius 6. Bright bone (1000) inside, soft tissue (50) outside
  const pixelBuf = Buffer.alloc(pixelCount * 2);
  const cx = (cols - 1) / 2;
  const cy = (rows - 1) / 2;
  const radius = Math.min(rows, cols) * 0.38;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const dr = r - cy;
      const dc = c - cx;
      const val = Math.sqrt(dr * dr + dc * dc) <= radius ? 1000 : 50;
      pixelBuf.writeUInt16LE(val, (r * cols + c) * 2);
    }
  }
  dsParts.push(encodeTag(0x7FE0, 0x0010, 'OW', pixelBuf));

  parts.push(Buffer.concat(dsParts));
  return Buffer.concat(parts);
}

function u16le(value: number): Buffer {
  const buf = Buffer.alloc(2);
  buf.writeUInt16LE(value, 0);
  return buf;
}

export function generateTestDicomFile(outputDir: string): {
  dcmPath: string;
  zipPath: string;
  seriesInstanceUID: string;
  studyInstanceUID: string;
} {
  // Unique per call so repeated test runs create a genuinely new series
  // instead of re-uploading the same fixed UID every time — that lets tests
  // identify "their" series by ID instead of diffing counts against
  // whatever old data already happens to be in the dataset.
  const unique = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const studyInstanceUID = `2.25.123456789.${unique}`;
  const seriesInstanceUID = `2.25.987654321.${unique}`;
  const sopInstanceUID = `1.3.6.1.4.1.5962.1.1.${unique}`;

  fs.mkdirSync(outputDir, { recursive: true });
  const dcmPath = path.join(outputDir, 'test-ct.dcm');
  fs.writeFileSync(dcmPath, createMinimalDicom(seriesInstanceUID, studyInstanceUID, sopInstanceUID));

  const zipPath = path.join(outputDir, 'test-ct.zip');
  if (fs.existsSync(zipPath)) fs.unlinkSync(zipPath);
  execSync(`zip -jq "${zipPath}" "${path.basename(dcmPath)}"`, {
    cwd: outputDir,
    stdio: 'pipe',
  });

  if (!fs.existsSync(zipPath)) {
    throw new Error(`Failed to create zip at ${zipPath}`);
  }

  return { dcmPath, zipPath, seriesInstanceUID, studyInstanceUID };
}

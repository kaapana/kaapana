// Parses the proxy's multipart/form-data responses: a JSON `meta` part and a binary `seg` part
// (empty when nothing changed). The browser already undid any Content-Encoding.

const HEADER_END = [13, 10, 13, 10]; // \r\n\r\n

function indexOf(haystack: Uint8Array, needle: ArrayLike<number>, from = 0): number {
  search: for (let i = from; i <= haystack.length - needle.length; i++) {
    for (let k = 0; k < needle.length; k++) {
      if (haystack[i + k] !== needle[k]) {
        continue search;
      }
    }
    return i;
  }
  return -1;
}

export function parseMultipart(
  body: ArrayBuffer,
  contentType: string
): { meta: Record<string, any>; seg: Uint8Array } {
  const boundary = /boundary="?([^";]+)"?/i.exec(contentType)?.[1];
  if (!boundary) {
    throw new Error('nnInteractive response has no multipart boundary');
  }
  const bytes = new Uint8Array(body);
  const delimiter = new TextEncoder().encode(`--${boundary}`);
  const decoder = new TextDecoder();
  const parts: Record<string, Uint8Array> = {};

  // Each part: --boundary\r\n<headers>\r\n\r\n<body>\r\n, up to the closing --boundary--.
  let start = indexOf(bytes, delimiter);
  while (start >= 0) {
    const headersStart = start + delimiter.length + 2;
    const next = indexOf(bytes, delimiter, headersStart);
    const headersEnd = indexOf(bytes, HEADER_END, headersStart);
    if (next < 0 || headersEnd < 0 || headersEnd > next) {
      break;
    }
    const name = /name="([^"]+)"/i.exec(
      decoder.decode(bytes.subarray(headersStart, headersEnd))
    )?.[1];
    if (name) {
      parts[name] = bytes.subarray(headersEnd + HEADER_END.length, next - 2);
    }
    start = next;
  }

  if (!parts.meta) {
    throw new Error('nnInteractive response has no meta part');
  }
  return { meta: JSON.parse(decoder.decode(parts.meta)), seg: parts.seg ?? new Uint8Array(0) };
}

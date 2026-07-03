import type { LogLine } from '@/types/schemas'

export function logLinesToText(lines: LogLine[]): string {
  return lines
    .map((l: LogLine) => `${l.time.slice(0, 19).replace('T', ' ')}  ${l.severity.padEnd(8)}  ${l.message}`)
    .join('\n')
}

import { workflowRunsApi } from '@/api/workflowRuns'
import { logLinesToText } from '@/utils/logFormat'
import { downloadAsZip } from '@/utils/zipDownload'
import type { LogLine, TaskRun } from '@/types/schemas'

export function downloadText(fileName: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/plain' }))
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * Downloads the logs of all tasks as one ZIP file. Returns the titles of the
 * tasks whose logs could not be fetched; their files in the archive say so.
 */
export async function downloadRunLogs(
  zipName: string,
  workflowRunId: number,
  taskRuns: TaskRun[],
  cached?: Map<number, LogLine[]>,
): Promise<string[]> {
  const failed: string[] = []
  const entries = await Promise.all(
    taskRuns.map(async (task) => {
      try {
        const lines =
          cached?.get(task.id) ?? (await workflowRunsApi.getTaskRunLogLines(workflowRunId, task.id))
        return { name: `${task.task_title}.log`, content: logLinesToText(lines) }
      } catch {
        failed.push(task.task_title)
        return {
          name: `${task.task_title}.log`,
          content: 'The logs of this task could not be fetched.',
        }
      }
    }),
  )
  downloadAsZip(zipName, entries)
  return failed
}

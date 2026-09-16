import { httpClient } from '@kaapana/base-ui'

// One entry of the results listing. Folders carry `file: false`, result files a
// type string. `hasChildren` distinguishes the two before any child is loaded,
// because the backend sends an empty `children` array on files as well.
export interface ResultsTreeNode {
  name: string
  path: string
  url?: string
  file?: string | false
  children?: ResultsTreeNode[]
  hasChildren?: boolean
}

// One directory level. A non-null token means the level has more entries.
export interface ResultsTreePage {
  items: ResultsTreeNode[]
  nextContinuationToken: string | null
}

export interface ResultsTreeQuery {
  // Folder to list. Omitted for the top level.
  prefix?: string
  // Token from the previous page of the same level.
  continuationToken?: string | null
  limit: number
}

/**
 * Fetch one page of one directory level of the workflow results.
 *
 * The path stays relative to the service, because the shared httpClient
 * rewrites it onto the project the document URL selects.
 */
export async function fetchResultsTree(query: ResultsTreeQuery): Promise<ResultsTreePage> {
  const { data } = await httpClient.get<Partial<ResultsTreePage>>(
    '/kaapana-backend/get-static-website-results-tree',
    {
      params: {
        prefix: query.prefix || undefined,
        continuation_token: query.continuationToken || undefined,
        limit: query.limit,
      },
    },
  )
  return {
    items: data?.items ?? [],
    nextContinuationToken: data?.nextContinuationToken ?? null,
  }
}

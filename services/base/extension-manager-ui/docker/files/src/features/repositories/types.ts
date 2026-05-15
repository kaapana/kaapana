import type { Repository } from '@/shared/types/apiSchemas'

export interface RepositoryFormState {
  name: string
  description: string
  repository_url: string
  authentication: string
}

export type RepositoryDict = Record<string, Repository>

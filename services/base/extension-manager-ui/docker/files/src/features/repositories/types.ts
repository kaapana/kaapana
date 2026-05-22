import type { Repository } from '@/shared/types/apiSchemas'

export interface RepositoryFormState {
  name: string
  description: string
  repository_url: string
  username: string
  password: string
}

export type RepositoryDict = Record<string, Repository>

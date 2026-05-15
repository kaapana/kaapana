import type {
  CreateRepositoryRequest,
  Repository,
  UpdateRepositoryRequest,
} from '@/shared/types/apiSchemas'
import type { RepositoryFormState } from '@/features/repositories/types'

export function createFormState(repository?: Repository): RepositoryFormState {
  return {
    name: repository?.name ?? '',
    description: repository?.description ?? '',
    repository_url: repository?.repository_url ?? '',
    authentication: '',
  }
}

export function toCreateRequest(form: RepositoryFormState): CreateRepositoryRequest {
  return {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    repository_url: form.repository_url.trim(),
    authentication: form.authentication.trim(),
  }
}

export function toUpdateRequest(form: RepositoryFormState): UpdateRepositoryRequest {
  return {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    repository_url: form.repository_url.trim(),
    authentication: form.authentication.trim() || undefined,
  }
}

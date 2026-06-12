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
    username: '',
    password: '',
  }
}

export function toCreateRequest(form: RepositoryFormState): CreateRepositoryRequest {
  return {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    repository_url: form.repository_url.trim(),
    username: form.username.trim(),
    password: form.password,
  }
}

export function toUpdateRequest(form: RepositoryFormState): UpdateRepositoryRequest {
  const request: UpdateRepositoryRequest = {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    repository_url: form.repository_url.trim(),
  }

  // Only send credentials if entered -> an edit can leave them
  // blank to keep the stored ones in partial update
  const username = form.username.trim()
  if (username) request.username = username
  if (form.password) request.password = form.password

  return request
}

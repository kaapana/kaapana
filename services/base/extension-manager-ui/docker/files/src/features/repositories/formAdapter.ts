import type {
  CreateRepositoryRequest,
  Repository,
  UpdateRepositoryRequest,
} from '@/shared/types/apiSchemas'
import type { RepositoryFormState } from '@/features/repositories/types'

export function createFormState(repository?: Repository | null): RepositoryFormState {
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
    description: form.description.trim(),
    repository_url: form.repository_url.trim(),
    username: form.username.trim(),
    password: form.password,
  }
}

export function toUpdateRequest(form: RepositoryFormState): UpdateRepositoryRequest {
  const request: UpdateRepositoryRequest = {
    name: form.name.trim(),
    description: form.description.trim(),
    repository_url: form.repository_url.trim(),
  }
  const username = form.username.trim()
  if (username && form.password) {
    request.username = username
    request.password = form.password
  }
  return request
}

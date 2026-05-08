import axios from 'axios'

// Requests go through the OAuth2 proxy – browser session cookie handles auth automatically.
// No token/secret needed in the frontend.
export const lokiApiClient = axios.create({
  baseURL: '/loki/api/v1',
  timeout: 15_000,
})

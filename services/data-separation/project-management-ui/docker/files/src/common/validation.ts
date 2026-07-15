export const projectNameRules: Array<(value: string) => boolean | string> = [
  (v) => !!v || 'Required.',
  (v) => v.length <= 13 || 'Max 13 characters',
  (v) => v === v.toLowerCase() || 'Only lowercase characters are supported',
  (v) => !v.includes(' ') || 'Spaces are not allowed',
  (v) => v !== 'admin' || 'Name "admin" is reserved',
]

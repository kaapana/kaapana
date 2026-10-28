export const required = (what: string) => (v: string) => !!v?.trim() || `Enter ${what}.`

export const projectNameHint =
  'At most 13 lowercase letters, digits and hyphens. The name also identifies the project ' +
  'in DICOM transfers, so DICOM AE title rules apply. Avoid the word "project" in the name.'

export const projectNameRules: Array<(value: string) => boolean | string> = [
  required('a project name'),
  (v) => v.length <= 13 || `Use at most 13 characters; this name has ${v.length}.`,
  (v) => v === v.toLowerCase() || 'Use lowercase; capital letters are not allowed.',
  (v) => !v.includes(' ') || 'Remove the spaces; use - to separate words.',
  (v) => /^[a-z0-9-]*$/.test(v) || 'Use only lowercase letters, digits and hyphens.',
  (v) => v !== 'admin' || 'The name "admin" is reserved; choose another name.',
]

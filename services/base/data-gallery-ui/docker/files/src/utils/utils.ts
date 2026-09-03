export function debounce<T extends (...args: any[]) => void>(
  fn: T,
  delay: number,
): (...args: Parameters<T>) => void {
  let timeoutID: ReturnType<typeof setTimeout> | null = null
  return function (this: unknown, ...args: Parameters<T>) {
    if (timeoutID) clearTimeout(timeoutID)
    timeoutID = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

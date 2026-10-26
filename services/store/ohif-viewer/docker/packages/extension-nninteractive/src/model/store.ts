// Minimal observable store. Panels subscribe instead of polling; models push
// changes through set(). Kept deliberately tiny (Ponytail: only what must exist).

export type Unsubscribe = () => void;

export interface Store<T extends object> {
  get(): Readonly<T>;
  set(patch: Partial<T>): void;
  update(fn: (prev: Readonly<T>) => Partial<T>): void;
  subscribe(listener: () => void): Unsubscribe;
}

export function createStore<T extends object>(initial: T): Store<T> {
  let state: T = { ...initial };
  const listeners = new Set<() => void>();

  const notify = () => {
    listeners.forEach(listener => {
      try {
        listener();
      } catch (error) {
        console.warn('nnInteractive store listener failed:', error);
      }
    });
  };

  return {
    get: () => state,
    set: (patch: Partial<T>) => {
      state = { ...state, ...patch };
      notify();
    },
    update: (fn: (prev: Readonly<T>) => Partial<T>) => {
      state = { ...state, ...fn(state) };
      notify();
    },
    subscribe: (listener: () => void) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

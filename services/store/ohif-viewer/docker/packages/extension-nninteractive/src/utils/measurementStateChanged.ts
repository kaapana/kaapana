export const MEASUREMENT_STATE_CHANGED_EVENT = 'measurement-state-changed';

export function dispatchMeasurementStateChanged() {
  if (typeof document === 'undefined') {
    return;
  }

  document.dispatchEvent(new Event(MEASUREMENT_STATE_CHANGED_EVENT));
}

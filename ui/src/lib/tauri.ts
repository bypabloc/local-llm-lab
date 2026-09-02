export function isTauri(): boolean {
  const w = window as unknown as { __TAURI_INTERNALS__?: unknown }
  return w.__TAURI_INTERNALS__ !== undefined
}

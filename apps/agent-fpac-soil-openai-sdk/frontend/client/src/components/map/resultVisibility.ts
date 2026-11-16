import type { ScreeningStatus } from './useScreening';

// Only a new successful screening overrides the user's result visibility choice.
export function showNewScreeningResult(
  previous: ScreeningStatus,
  current: ScreeningStatus,
  setVisible: (visible: boolean) => void,
) {
  if (previous !== 'done' && current === 'done') setVisible(true);
}

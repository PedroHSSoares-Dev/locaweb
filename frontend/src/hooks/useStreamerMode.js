import { useCallback, useEffect, useState } from 'react';
import {
  readStreamerMode,
  subscribeToStreamerMode,
  writeStreamerMode,
} from '../utils/privacy';

export function useStreamerMode(email) {
  const [streamerMode, setStreamerModeState] = useState(() => readStreamerMode(email));

  useEffect(() => subscribeToStreamerMode(email, setStreamerModeState), [email]);

  const setStreamerMode = useCallback((enabled) => {
    const nextValue = typeof enabled === 'function'
      ? enabled(readStreamerMode(email))
      : enabled;
    setStreamerModeState(Boolean(nextValue));
    writeStreamerMode(email, nextValue);
  }, [email]);

  const toggleStreamerMode = useCallback(() => {
    setStreamerMode((current) => !current);
  }, [setStreamerMode]);

  return { streamerMode, setStreamerMode, toggleStreamerMode };
}

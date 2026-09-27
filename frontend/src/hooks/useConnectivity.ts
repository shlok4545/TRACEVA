import { useEffect, useState } from 'react';

import type { ConnectivityState } from '../components/ui/ConnectivityIndicator';

export function useConnectivity() {
  const [state, setState] = useState<ConnectivityState>(() => (navigator.onLine ? 'ONLINE' : 'OFFLINE'));
  const [lastChangedAt, setLastChangedAt] = useState<string>(new Date().toISOString());

  useEffect(() => {
    const onOnline = () => {
      setState('ONLINE');
      setLastChangedAt(new Date().toISOString());
    };

    const onOffline = () => {
      setState('OFFLINE');
      setLastChangedAt(new Date().toISOString());
    };

    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);

    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, []);

  return { state, lastChangedAt };
}

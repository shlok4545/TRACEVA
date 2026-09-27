import { useEffect, useState } from 'react';

import { api } from '../services/api';

export function useApiHealth() {
  const [status, setStatus] = useState<'Connected' | 'Disconnected'>('Disconnected');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const response = await api.getHealth();
        if (isMounted) {
          setStatus(response?.status === 'ok' ? 'Connected' : 'Disconnected');
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setStatus('Disconnected');
          setError(err instanceof Error ? err.message : 'Backend unavailable');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, []);

  return { status, loading, error };
}

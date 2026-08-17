import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://atfozkznxxuehyjgqvvm.supabase.co';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_B1hsywJt3jKSDdij-3iddw_ZNStwZWY';

// Initialize lightweight Supabase client with Realtime WebSockets enabled
export const supabaseRealtimeClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  realtime: {
    params: {
      eventsPerSecond: 10,
    },
  },
});

/**
 * Subscribes to real-time database changes for announcements and notifications.
 * ZERO HTTP polling - pushes directly over a single persistent WebSocket.
 *
 * @param {Function} onNewNotification - Callback fired when a new notification/announcement arrives
 * @returns {Function} Unsubscribe function to clean up WebSocket channel on component unmount
 */
export function subscribeToRealtimeNotifications(onNewNotification) {
  try {
    const channel = supabaseRealtimeClient
      .channel('public:system_events')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'announcements' },
        (payload) => {
          if (payload && payload.new && typeof onNewNotification === 'function') {
            onNewNotification({
              id: payload.new.id || payload.new.announcement_id || Date.now(),
              title: payload.new.title || '📢 System Announcement',
              message: payload.new.message || payload.new.content || '',
              time: 'Just now',
              read: false,
            });
          }
        }
      )
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'notifications' },
        (payload) => {
          if (payload && payload.new && typeof onNewNotification === 'function') {
            onNewNotification({
              id: payload.new.id || Date.now(),
              title: payload.new.title || '🔔 Notification',
              message: payload.new.message || payload.new.text || '',
              time: 'Just now',
              read: false,
            });
          }
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.info('🔌 Supabase Realtime WebSocket connected. Listening for zero-polling push events.');
        }
      });

    return () => {
      supabaseRealtimeClient.removeChannel(channel);
    };
  } catch (err) {
    console.warn('Realtime subscription fallback notice:', err);
    return () => {};
  }
}

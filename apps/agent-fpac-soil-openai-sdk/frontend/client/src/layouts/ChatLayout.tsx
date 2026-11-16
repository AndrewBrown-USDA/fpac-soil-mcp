import { useCallback, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Map as MapIcon } from 'lucide-react';
import { AppSidebar } from '@/components/app-sidebar';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { useSession } from '@/contexts/SessionContext';
import { DatabricksLogo } from '@/components/DatabricksLogo';
import { DbIcon } from '@/components/ui/db-icon';
import { UserKeyIconIcon } from '@/components/icons';
import { MapPanel } from '@/components/map/MapPanel';
import { ActiveAoiProvider } from '@/components/map/ActiveAoiContext';
import { ActiveCorridorProvider } from '@/components/map/ActiveCorridorContext';
import { MapResultProvider } from '@/components/map/MapResultContext';

export default function ChatLayout() {
  const { session, loading } = useSession();
  const isCollapsed = localStorage.getItem('sidebar:state') !== 'true';
  // Open beside the chat on md+ screens; behind the toggle on narrow screens.
  const [mapOpen, setMapOpen] = useState(
    () => window.matchMedia?.('(min-width: 768px)').matches ?? false,
  );
  // "Show on map" on a tool card opens the panel.
  const openMap = useCallback(() => setMapOpen(true), []);

  // Wait for session to load
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  // No guest mode - redirect if no session
  if (!session?.user) {
    return (
      <div className="flex h-screen items-center justify-center bg-secondary">
        <div className="flex flex-col items-center gap-6">
          <DatabricksLogo height={20} />
          <div className="flex w-80 flex-col items-center gap-4 rounded-md border border-border bg-background p-10 shadow-[var(--shadow-db-lg)]">
            <DbIcon icon={UserKeyIconIcon} size={32} color="muted" />
            <div className="flex flex-col items-center gap-1.5 text-center">
              <h3>Authentication Required</h3>
              <p className="text-muted-foreground">
                Please authenticate using Databricks to access this application.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Get preferred username from session (if available from headers)
  const preferredUsername = session.user.preferredUsername ?? null;

  return (
    <SidebarProvider defaultOpen={!isCollapsed}>
      <ActiveAoiProvider>
      <ActiveCorridorProvider>
        <MapResultProvider onShow={openMap}>
        <AppSidebar user={session.user} preferredUsername={preferredUsername} />
        <aside
          aria-label="Map panel"
          className={`relative h-svh shrink-0 bg-secondary ${mapOpen ? 'w-full md:w-[40%]' : 'w-10'}`}
        >
          {!mapOpen && (
            <button
              type="button"
              onClick={() => setMapOpen(true)}
              aria-expanded={false}
              aria-controls="map-panel"
              className="absolute top-2 right-1 z-10 flex flex-col items-center gap-0.5 rounded-md border border-border bg-background px-1.5 py-1 font-medium text-xs shadow-sm hover:bg-[var(--action-default-background-hover)] focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2"
            >
              <MapIcon aria-hidden="true" className="size-4 text-primary" />
              Map
            </button>
          )}
          <div
            id="map-panel"
            hidden={!mapOpen}
            className="h-full md:my-2 md:ml-2 md:rounded-xl md:bg-background"
          >
            <MapPanel onCloseMap={() => setMapOpen(false)} />
          </div>
        </aside>
        <SidebarInset className="h-svh overflow-hidden bg-secondary">
          <div className="flex flex-1 flex-col overflow-hidden bg-background md:my-2 md:mr-2 md:rounded-xl">
            <Outlet />
          </div>
        </SidebarInset>
        </MapResultProvider>
      </ActiveCorridorProvider>
      </ActiveAoiProvider>
    </SidebarProvider>
  );
}

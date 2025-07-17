# Real-Time Update System with WebSockets - Implementation Plan

## Overview

Implement a WebSocket-based real-time update system to automatically refresh both admin and user views when session state changes occur, eliminating the need for manual page refreshes.

## Current Architecture Analysis

- **Backend**: FastAPI with async SQLite database (aiosqlite)
- **Frontend**: Vanilla JS + Tailwind CSS
- **Session Management**: Database-driven with active/inactive states
- **Current Update Method**: Manual page refresh after actions

## Implementation Plan

### Phase 1: Backend WebSocket Infrastructure

#### 1.1 Add WebSocket Dependencies

- Add `websockets` to pyproject.toml dependencies
- Update FastAPI to support WebSocket connections

#### 1.2 WebSocket Manager Service (`app/websocket_manager.py`)

```python
class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {
            "admin": [],      # Admin connections
            "users": []       # User connections
        }

    async def connect(self, websocket: WebSocket, client_type: str)
    async def disconnect(self, websocket: WebSocket, client_type: str)
    async def broadcast_to_group(self, group: str, message: dict)
    async def broadcast_session_update(self, event_type: str, session_data: dict)
```

#### 1.3 WebSocket Event Types

```python
# Event types for real-time updates
SESSION_EVENTS = {
    "SESSION_CREATED": "session_created",
    "SESSION_STARTED": "session_started",
    "SESSION_FINISHED": "session_finished",
    "MEMES_POPULATED": "memes_populated",
    "NEW_RATING": "new_rating",
    "STATS_UPDATED": "stats_updated"
}
```

#### 1.4 Enhanced Database Layer

- Add event broadcasting to session operations:
  - `create_session()` → broadcast SESSION_CREATED
  - `start_session()` → broadcast SESSION_STARTED
  - `end_session()` → broadcast SESSION_FINISHED
  - `create_ranking()` → broadcast NEW_RATING + STATS_UPDATED

#### 1.5 WebSocket Endpoints (`app/main.py`)

```python
@app.websocket("/ws/admin")
async def websocket_admin_endpoint(websocket: WebSocket)

@app.websocket("/ws/user")
async def websocket_user_endpoint(websocket: WebSocket)
```

### Phase 2: Frontend WebSocket Client

#### 2.1 WebSocket Service (`static/js/websocket.js`)

```javascript
class WebSocketService {
    constructor(endpoint, reconnectInterval = 5000) {
        this.endpoint = endpoint;
        this.reconnectInterval = reconnectInterval;
        this.eventHandlers = new Map();
        this.connect();
    }

    connect()
    disconnect()
    onMessage(event)
    addEventListener(eventType, handler)
    removeEventListener(eventType, handler)
    send(data)
    handleReconnect()
}
```

#### 2.2 Admin Dashboard Real-Time Updates

- **Auto-refresh triggers**:
  - Session created/started/finished → Update session info card
  - New ratings → Update statistics cards and meme grid
  - Memes populated → Refresh meme statistics
- **Visual indicators**: Show "live" status indicator when connected
- **Graceful degradation**: Fall back to polling if WebSocket fails

#### 2.3 User View Real-Time Updates

- **Auto-refresh triggers**:
  - Session started → Show new meme if available
  - Session finished → Show completion screen
  - No active session → Show waiting message
- **Progress updates**: Real-time progress bar updates
- **Seamless experience**: No interruption to current rating process

### Phase 3: Enhanced User Experience

#### 3.1 Connection Status Indicators

```javascript
// Visual indicators for connection status
const indicators = {
    connected: "🟢 Live",
    disconnected: "🔴 Disconnected",
    reconnecting: "🟡 Reconnecting..."
}
```

#### 3.2 Smart Update Strategies

- **Admin Dashboard**:

  - Partial updates for statistics (no full page reload)
  - Smooth transitions for session state changes
  - Real-time participant count (future enhancement)

- **User View**:

  - Preserve current rating input during updates
  - Queue updates during active rating process
  - Smart notification system for important changes

#### 3.3 Offline Handling

- Detect offline/online state
- Queue actions when offline
- Sync when connection restored
- Show appropriate user feedback

### Phase 4: Performance & Reliability

#### 4.1 Connection Management

- Automatic reconnection with exponential backoff
- Connection pooling and cleanup
- Heartbeat/ping mechanism to detect dead connections
- Rate limiting for WebSocket messages

#### 4.2 Data Efficiency

- Send only essential data in WebSocket messages
- Use incremental updates instead of full refreshes
- Implement message queuing for high-traffic scenarios

#### 4.3 Error Handling

- Graceful degradation when WebSocket unavailable
- Fallback to HTTP polling for critical updates
- User-friendly error messages
- Logging for debugging WebSocket issues

### Phase 5: Advanced Features (Future)

#### 5.1 Real-Time Notifications

- Toast notifications for important events
- Sound notifications (optional)
- Browser push notifications when tab not active

#### 5.2 Live Session Monitoring

- Real-time participant list in admin dashboard
- Live rating activity feed
- Session analytics dashboard

#### 5.3 Collaborative Features

- Show when other users are rating
- Live leaderboard updates
- Real-time session chat (optional)

## File Structure Changes

```
app/
├── websocket_manager.py     # NEW: WebSocket connection manager
├── events.py               # NEW: Event definitions and broadcasting
├── main.py                 # MODIFIED: Add WebSocket endpoints
└── database.py             # MODIFIED: Add event broadcasting

static/js/
├── websocket.js           # NEW: WebSocket client service
├── admin-realtime.js      # NEW: Admin dashboard real-time logic
├── user-realtime.js       # NEW: User view real-time logic
└── app.js                 # MODIFIED: Integration with WebSocket

templates/
├── admin.html             # MODIFIED: Add connection status indicator
├── index.html             # MODIFIED: Add connection status indicator
└── base.html              # MODIFIED: Include WebSocket scripts
```

## Implementation Priority

1. **High Priority** (Core functionality):

   - WebSocket infrastructure
   - Basic session event broadcasting
   - Admin dashboard auto-refresh

1. **Medium Priority** (User experience):

   - User view auto-refresh
   - Connection status indicators
   - Graceful error handling

1. **Low Priority** (Enhancements):

   - Advanced notifications
   - Offline handling
   - Performance optimizations

## Testing Strategy

1. **Unit Tests**: WebSocket manager and event broadcasting
1. **Integration Tests**: End-to-end WebSocket communication
1. **Load Testing**: Multiple concurrent WebSocket connections
1. **User Testing**: Verify seamless real-time experience

## Migration Strategy

1. **Backward Compatibility**: Keep existing refresh mechanisms as fallback
1. **Progressive Enhancement**: Add WebSocket as enhancement layer
1. **Feature Flags**: Allow enabling/disabling real-time features
1. **Monitoring**: Track WebSocket connection health and performance

This implementation will provide a modern, responsive user experience where changes are reflected immediately across all connected clients, making the meme ranking sessions feel more dynamic and engaging.

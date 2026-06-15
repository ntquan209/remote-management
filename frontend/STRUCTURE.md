# Frontend Structure

## Cấu trúc dự án

```
frontend/
├── public/
│   └── index.html              # Entry point (10 dòng - shell nhẹ)
│
├── src/
│   ├── index.js                # Main entry point (Module ES6+)
│   │
│   ├── templates/              # HTML templates (dynamic rendering)
│   │   ├── sidebar.js          # Sidebar UI
│   │   ├── topbar.js           # Top navigation bar
│   │   ├── panels.js           # 8 content panels (dashboard, apps, processes, etc.)
│   │   └── renderer.js         # Template renderer (renderApp function)
│   │
│   ├── assets/                 # Static assets (images, fonts, icons, ...)
│   │   └── [images, etc.]
│   │
│   ├── components/             # Reusable UI components
│   │   └── machine-selector.js # Machine/agent selector logic
│   │
│   ├── lib/                    # External library wrappers
│   │   └── socket.js           # Socket.io client wrapper
│   │
│   ├── utils/                  # Helper functions
│   │   ├── dom.js              # DOM manipulation utilities
│   │   └── audit.js            # Audit log utilities
│   │
│   ├── config/                 # Application configuration
│   │   └── app.config.js       # App constants & settings
│   │
│   ├── styles/                 # Stylesheets
│   │   └── style.css           # Main theme styles
│   │
│   └── pages/                  # Feature/page modules
│       ├── monitor.js          # Screen & process monitoring
│       └── control.js          # Webcam & power control
│
└── STRUCTURE.md                # This file
```

## File Organization

### `public/index.html`
- Ultra-lightweight entry point (10 lines)
- Loads CSS, Socket.io, and main module
- Contains only a single `<div class="app"></div>` container
- All HTML is rendered dynamically

### `src/index.js`
- Application entry point
- Imports templates, initializes Socket.io
- Sets up event listeners for all features
- Exposes global functions for onclick handlers

### `src/templates/`
- **sidebar.js**: Navigation sidebar (list of features)
- **topbar.js**: Machine selector & status bar
- **panels.js**: All 8 content panels (dashboard, apps, processes, screen, keylog, files, webcam, power)
- **renderer.js**: Main renderApp() function that assembles all templates

### `src/components/`
- **machine-selector.js**: Machine online/offline logic, dropdown management, status updates

### `src/lib/`
- **socket.js**: Socket.io wrapper (initSocket, getSocket, emitCommand)

### `src/utils/`
- **dom.js**: DOM helpers (getElementById, switchPanel, updateElement, setHTML, enableButton)
- **audit.js**: Audit log management (addAuditRow, logSystemEvent)

### `src/config/`
- **app.config.js**: App name, version, socket URL, timeouts

### `src/pages/`
- **monitor.js**: handleScreenTrigger, handleProcesses
- **control.js**: handleWebcamTrigger, handlePowerCommand, keylogger controls

### `src/styles/`
- **style.css**: All application styles (imported in public/index.html)

## Usage Examples

### Adding a new feature:
1. Create template in `src/templates/myfeature.js`
2. Create logic in `src/pages/myfeature.js`
3. Import in `src/index.js`
4. Update `src/templates/renderer.js` to include template

### Adding a component:
1. Create in `src/components/mycomponent.js`
2. Import where needed
3. Use in pages or templates

### Working with DOM:
```javascript
import { getElementById, switchPanel, updateElement } from './utils/dom.js';

// Get element
const el = getElementById('some-id');

// Update text
updateElement('stat-val', '42');

// Switch panel
switchPanel('dashboard', navElement);
```

### Working with Socket.io:
```javascript
import { getSocket, emitCommand } from './lib/socket.js';

const socket = getSocket();
socket.on('event', (data) => { /* ... */ });

// Emit command
emitCommand('SCREENSHOT', 'machine-name');
```

## Cài đặt & chạy frontend
1. Mở terminal và vào thư mục `frontend`:

   cd frontend

2. Cài đặt dependency:

   npm install

3. Chạy frontend bằng Vite:

   npm run dev

4. Mở trình duyệt tới địa chỉ Vite cung cấp (thường là `http://localhost:5173`).

> Nếu dùng Windows và lệnh `npm` không chạy, kiểm tra cài đặt Node.js và dùng `npm.cmd` nếu cần.



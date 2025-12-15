# Magentic AI Chat - React Frontend

Professional React frontend for multi-agent AI assistant with real-time streaming.

**Built with React 19 and Vite** for lightning-fast development and optimized production builds.

## Features

- 🎨 **Clean Split UI**: Chat on the right, internal process on the left
- 📊 **Real-time Streaming**: See orchestrator planning and agent work live
- 🎯 **Collapsible Sections**: Expand/collapse orchestrator and individual agents
- 🎭 **Material-UI**: Professional, responsive design
- 🔄 **WebSocket**: Low-latency real-time updates
- 👁️ **Toggle Process View**: Show/hide internal thinking
- ⚡ **Vite**: Instant HMR and fast builds

## Quick Start

1. Install dependencies:

   ```bash
   cd react-frontend
   npm install
   ```

1. Configure backend URL (optional):

   Create `.env` file:

   ```env
   VITE_BACKEND_URL=http://localhost:7000
   ```

1. Start the development server:

   ```bash
   npm run dev
   ```

The app will automatically open at <http://localhost:3000>

## Available Commands

```bash
npm run dev      # Start development server with HMR
npm run build    # Build for production (output: dist/)
npm run preview  # Preview production build locally
npm run lint     # Run ESLint
```

## Usage

1. Type your question in the input box
2. Press Enter or click Send
3. Watch the internal process on the left (orchestrator planning, agents working)
4. See the final answer in the main chat area
5. Click the eye icon to hide/show the internal process panel

## Production Build

```bash
npm run build
```

Builds the optimized production bundle to the `dist/` directory.

To preview the production build locally:

```bash
npm run preview
```

## Docker Deployment

Build and run with Docker:

```bash
# Build the image
docker build -t magentic-react-frontend .

# Run the container
docker run -d -p 3000:3000 magentic-react-frontend
```

Access at <http://localhost:3000>

## Documentation

- � **[Vite Migration Guide](VITE_MIGRATION.md)** - Complete migration details
- 🔄 **[React 19 Migration](REACT_19_MIGRATION.md)** - React 19 upgrade guide
- 📋 **[Migration Summary](MIGRATION_SUMMARY.md)** - Quick reference
- 🚀 **[Quick Start](QUICK_START.md)** - Fast setup guide
- 🐛 **[Error Handling](ERROR_HANDLING.md)** - Error handling system
- 🔧 **[Refactoring Guide](REFACTORING.md)** - Component architecture

## Technology Stack

- **React 19** - UI library with latest features
- **Vite 7** - Build tool and dev server
- **Material-UI 7** - Component library (React 19 compatible)
- **MSAL** - Microsoft authentication
- **WebSocket** - Real-time communication
- **React Markdown** - Message rendering

# Build & Integration Guide

## Step 1: Install Dependencies

```bash
cd packages/dashboard/src/frontend
npm install
```

This will install:
- React 18 and dependencies
- TypeScript and type definitions
- Vite build tool
- Recharts, Cytoscape, and other visualization libraries
- React Router, Axios, and other utilities

## Step 2: Type Checking

After installing dependencies, run type checking:

```bash
npx tsc --noEmit
```

This validates:
- TypeScript type correctness
- Import/export consistency
- Component prop types
- API interface compatibility

## Step 3: Build for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

## Step 4: Development Server

For local development:

```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

## Step 5: Backend Integration

### Start Backend Server

```bash
cd packages/dashboard
python -m uvicorn src.api.server:app --reload --port 8080
```

### Verify Backend Endpoints

1. **Health Check**:
   ```bash
   curl http://localhost:8080/api/v1/health
   ```

2. **Get Deployments**:
   ```bash
   curl http://localhost:8080/api/v1/deployments
   ```

3. **Get Deployment Metrics**:
   ```bash
   curl http://localhost:8080/api/v1/deployments/{id}/metrics
   ```

### WebSocket Endpoints

The backend provides:
- `ws://localhost:8080/ws/metrics/{deployment_id}` - Real-time metrics
- `ws://localhost:8080/ws/alerts` - Real-time alerts
- `ws://localhost:8080/ws/collaboration/{deployment_id}` - Collaboration (if implemented)

## Integration Checklist

- [ ] Dependencies installed (`npm install`)
- [ ] Type checking passes (`npx tsc --noEmit`)
- [ ] Build succeeds (`npm run build`)
- [ ] Backend server running on port 8080
- [ ] CORS configured correctly
- [ ] WebSocket connections working
- [ ] Real-time updates functioning
- [ ] API endpoints responding

## Troubleshooting

### Type Errors
- Run `npm install` to ensure all type definitions are available
- Check `tsconfig.json` configuration

### Build Errors
- Verify all imports are correct
- Check for missing dependencies in `package.json`

### Backend Connection Errors
- Verify backend server is running
- Check CORS configuration
- Verify API endpoint paths match frontend expectations

### WebSocket Errors
- Verify WebSocket endpoint URLs
- Check backend WebSocket implementation
- Verify connection handling in frontend


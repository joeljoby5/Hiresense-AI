import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { LandingPage, Workspace, WorkspaceError, WorkspaceHelp } from './Workspace'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, staleTime: 15_000 },
    mutations: { retry: false },
  },
})

const loading = <main className="workspace-content" role="status">Loading workspace…</main>

const router = createBrowserRouter([
  { path: '/', Component: LandingPage },
  {
    path: '/workspace',
    Component: Workspace,
    hydrateFallbackElement: loading,
    children: [
      { index: true, lazy: async () => ({ Component: (await import('../features/resumes/ResumeLibrary')).Overview }) },
      { path: 'resumes', lazy: async () => ({ Component: (await import('../features/resumes/ResumeLibrary')).ResumeLibrary }) },
      { path: 'resumes/:resumeId', lazy: async () => ({ Component: (await import('../features/resumes/ResumeDetail')).ResumeDetail }) },
      { path: 'resumes/:resumeId/edit', lazy: async () => ({ Component: (await import('../features/resumes/ResumeEditor')).ResumeEditor }) },
      { path: 'help', Component: WorkspaceHelp },
      { path: '*', Component: WorkspaceError },
    ],
    errorElement: <WorkspaceError />,
  },
  { path: '*', Component: WorkspaceError },
])

export function App() {
  return <QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>
}

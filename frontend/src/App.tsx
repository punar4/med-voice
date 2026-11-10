import CaregiverLog from './pages/CaregiverLog'
import CaregiverSetup from './pages/CaregiverSetup'
import Elder from './pages/Elder'

// Three pages, chosen from the URL: /elder/<share_token> is the elder's link,
// /log/<profile_id> is the caregiver's question log, and every other path is the
// caregiver setup. The token is the whole route, so no routing library is needed yet.
function App() {
  const elder = /^\/elder\/([^/]+)\/?$/.exec(window.location.pathname)
  if (elder) return <Elder token={decodeURIComponent(elder[1])} />

  const log = /^\/log\/(\d+)\/?$/.exec(window.location.pathname)
  if (log) return <CaregiverLog profileId={Number(log[1])} />

  return <CaregiverSetup />
}

export default App

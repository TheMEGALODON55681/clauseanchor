import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

/* Five font files the first screen can do without load once it has painted, so they do not
   compete with the script and style that paint it. The text sets in the fallback faces until
   they arrive. A browser with no paint timing loads them at once. */
const loadLateFonts = () => import('./fonts-late.css')
if (PerformanceObserver.supportedEntryTypes?.includes('paint')) {
  new PerformanceObserver((list, observer) => {
    if (!list.getEntriesByName('first-contentful-paint').length) return
    observer.disconnect()
    loadLateFonts()
  }).observe({ type: 'paint', buffered: true })
} else {
  loadLateFonts()
}

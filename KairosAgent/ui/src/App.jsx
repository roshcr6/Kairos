/**
 * Kairos Agent UI - Modern Edition
 * =================================
 * 
 * A beautiful, ethical UI that EXPLAINS what the agent is doing.
 * 
 * DESIGN PRINCIPLES:
 * 1. Glassmorphism & modern aesthetics
 * 2. Smooth animations & micro-interactions
 * 3. Trust through transparency
 * 4. Calm, non-judgmental language
 */

import { useState, useEffect, useCallback } from 'react'

// API base URL - proxied through Vite in dev, or direct in production
const API_BASE = '/api'

/**
 * Icons as SVG components for crisp rendering
 */
const Icons = {
  Clock: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
  ),
  Shield: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  ),
  Activity: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  Brain: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/>
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/>
    </svg>
  ),
  Eye: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  ),
  Zap: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  ),
  Target: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <circle cx="12" cy="12" r="6"/>
      <circle cx="12" cy="12" r="2"/>
    </svg>
  ),
  TrendingUp: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
      <polyline points="17 6 23 6 23 12"/>
    </svg>
  ),
  MessageCircle: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
    </svg>
  ),
  Wifi: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12.55a11 11 0 0 1 14.08 0"/>
      <path d="M1.42 9a16 16 0 0 1 21.16 0"/>
      <path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>
      <line x1="12" y1="20" x2="12.01" y2="20"/>
    </svg>
  ),
  WifiOff: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="1" y1="1" x2="23" y2="23"/>
      <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"/>
      <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"/>
      <path d="M10.71 5.05A16 16 0 0 1 22.58 9"/>
      <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"/>
      <path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>
      <line x1="12" y1="20" x2="12.01" y2="20"/>
    </svg>
  ),
  History: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v5h5"/>
      <path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/>
      <path d="M12 7v5l4 2"/>
    </svg>
  ),
  Sparkles: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
      <path d="M5 3v4"/>
      <path d="M19 17v4"/>
      <path d="M3 5h4"/>
      <path d="M17 19h4"/>
    </svg>
  )
}

/**
 * Format timestamp to human-readable time
 */
function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: true 
  })
}

/**
 * Get time ago string
 */
function getTimeAgo(isoString) {
  if (!isoString) return ''
  const now = new Date()
  const date = new Date(isoString)
  const seconds = Math.floor((now - date) / 1000)
  
  if (seconds < 60) return 'Just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return formatTime(isoString)
}

/**
 * Format intent for display (human-friendly)
 */
function formatIntent(intent) {
  const labels = {
    productive: 'Focused',
    neutral: 'Neutral',
    unproductive: 'Distracted',
    unknown: 'Observing'
  }
  return labels[intent] || intent
}

/**
 * Get intent icon
 */
function getIntentIcon(intent) {
  switch(intent) {
    case 'productive': return <Icons.Target />
    case 'unproductive': return <Icons.Activity />
    default: return <Icons.Eye />
  }
}

/**
 * Animated number component
 */
function AnimatedNumber({ value, suffix = '' }) {
  const [displayValue, setDisplayValue] = useState(0)
  
  useEffect(() => {
    const start = displayValue
    const end = value
    const duration = 500
    const startTime = Date.now()
    
    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
      setDisplayValue(Math.round(start + (end - start) * eased))
      
      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }
    
    requestAnimationFrame(animate)
  }, [value])
  
  return <>{displayValue}{suffix}</>
}

/**
 * Pulse animation for live indicator
 */
function PulseIndicator({ active }) {
  return (
    <span className={`pulse-indicator ${active ? 'active' : ''}`}>
      <span className="pulse-dot"></span>
      <span className="pulse-ring"></span>
    </span>
  )
}

/**
 * Agent Status Card - Modern Design
 */
function AgentStatusCard({ state, isConnected }) {
  if (!state) {
    return (
      <div className="card glass-card status-card-container">
        <div className="card-header">
          <Icons.Activity />
          <span>Agent Status</span>
        </div>
        <div className="loading-state">
          <div className="loader">
            <div className="loader-ring"></div>
            <Icons.Brain />
          </div>
          <p>Initializing agent...</p>
        </div>
      </div>
    )
  }

  const intentClass = `intent-${state.intent || 'unknown'}`
  const confidence = Math.round((state.confidence || 0) * 100)

  return (
    <div className="card glass-card status-card-container">
      <div className="card-header">
        <Icons.Activity />
        <span>Agent Status</span>
        <PulseIndicator active={isConnected} />
      </div>
      
      <div className="status-grid">
        <div className={`status-tile intent-tile ${intentClass}`}>
          <div className="tile-icon">
            {getIntentIcon(state.intent)}
          </div>
          <div className="tile-content">
            <span className="tile-label">Current State</span>
            <span className="tile-value">{formatIntent(state.intent)}</span>
          </div>
        </div>
        
        <div className="status-tile confidence-tile">
          <div className="tile-icon">
            <Icons.TrendingUp />
          </div>
          <div className="tile-content">
            <span className="tile-label">Confidence</span>
            <span className="tile-value">
              <AnimatedNumber value={confidence} suffix="%" />
            </span>
          </div>
          <div className="confidence-ring">
            <svg viewBox="0 0 36 36">
              <path
                className="confidence-bg"
                d="M18 2.0845
                  a 15.9155 15.9155 0 0 1 0 31.831
                  a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path
                className={`confidence-progress ${intentClass}`}
                strokeDasharray={`${confidence}, 100`}
                d="M18 2.0845
                  a 15.9155 15.9155 0 0 1 0 31.831
                  a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
          </div>
        </div>
      </div>
      
      <div className="focus-display">
        <div className="focus-icon">
          <Icons.Target />
        </div>
        <div className="focus-content">
          <span className="focus-label">Current Focus</span>
          <span className="focus-value">{state.focus_context || 'Initializing...'}</span>
        </div>
      </div>
    </div>
  )
}

/**
 * Last Decision Card - Modern Design
 */
function LastDecisionCard({ decision }) {
  if (!decision || decision.message) {
    return (
      <div className="card glass-card decision-card-container">
        <div className="card-header">
          <Icons.Brain />
          <span>Latest Insight</span>
        </div>
        <div className="empty-state">
          <div className="empty-icon">
            <Icons.Brain />
          </div>
          <h3>Learning in Progress</h3>
          <p>The agent is observing your patterns and will share insights soon.</p>
        </div>
      </div>
    )
  }

  const isNudge = decision.action === 'nudge'

  return (
    <div className={`card glass-card decision-card-container ${isNudge ? 'has-nudge' : ''}`}>
      <div className="card-header">
        <Icons.Brain />
        <span>Latest Insight</span>
        <span className="time-badge">{getTimeAgo(decision.timestamp)}</span>
      </div>
      
      <div className={`decision-content ${isNudge ? 'nudge-highlight' : ''}`}>
        <div className="decision-reasoning">
          {decision.reasoning}
        </div>
        
        {decision.nudge_message && (
          <div className="nudge-bubble">
            <div className="nudge-icon">
              <Icons.MessageCircle />
            </div>
            <p>{decision.nudge_message}</p>
          </div>
        )}
      </div>
      
      <div className="decision-footer">
        <span className="timestamp">
          <Icons.Clock />
          {formatTime(decision.timestamp)}
        </span>
        <span className={`action-chip ${decision.action}`}>
          {isNudge ? (
            <>
              <Icons.Sparkles />
              <span>Nudged</span>
            </>
          ) : (
            <>
              <Icons.Eye />
              <span>Observing</span>
            </>
          )}
        </span>
      </div>
    </div>
  )
}

/**
 * Reasoning Timeline - Modern Design
 */
function ReasoningTimeline({ timeline }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="card glass-card timeline-card-container">
        <div className="card-header">
          <Icons.History />
          <span>Activity Timeline</span>
        </div>
        <div className="empty-state">
          <div className="empty-icon">
            <Icons.History />
          </div>
          <h3>No Activity Yet</h3>
          <p>Your timeline will populate as the agent observes and reasons.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card glass-card timeline-card-container">
      <div className="card-header">
        <Icons.History />
        <span>Activity Timeline</span>
        <span className="count-badge">{timeline.length}</span>
      </div>
      
      <div className="timeline-list">
        {timeline.map((item, index) => (
          <div 
            key={index} 
            className={`timeline-entry ${item.action === 'nudge' ? 'nudge-entry' : ''}`}
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div className="timeline-marker">
              <span className={`marker-dot ${item.intent}`}></span>
              {index < timeline.length - 1 && <span className="marker-line"></span>}
            </div>
            
            <div className="timeline-content">
              <div className="timeline-header">
                <span className={`intent-badge ${item.intent}`}>
                  {getIntentIcon(item.intent)}
                  {formatIntent(item.intent)}
                </span>
                <span className="timeline-time">{formatTime(item.timestamp)}</span>
              </div>
              <p className="timeline-text">{item.reasoning}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Connection Status Banner - Modern Design
 */
function ConnectionStatus({ isConnected, lastUpdate }) {
  return (
    <div className={`connection-banner ${isConnected ? 'connected' : 'disconnected'}`}>
      <div className="connection-content">
        {isConnected ? <Icons.Wifi /> : <Icons.WifiOff />}
        <span className="connection-text">
          {isConnected ? 'Connected to Kairos Agent' : 'Reconnecting...'}
        </span>
      </div>
      {isConnected && lastUpdate && (
        <span className="last-update">Updated {getTimeAgo(lastUpdate)}</span>
      )}
    </div>
  )
}

/**
 * Error Banner
 */
function ErrorBanner({ message }) {
  return (
    <div className="error-banner">
      <div className="error-content">
        <Icons.WifiOff />
        <div>
          <p className="error-message">{message}</p>
          <p className="error-hint">Make sure the Kairos Agent is running on your machine.</p>
        </div>
      </div>
    </div>
  )
}

/**
 * Main App Component
 */
function App() {
  const [state, setState] = useState(null)
  const [decision, setDecision] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const [stateRes, decisionRes, timelineRes] = await Promise.all([
        fetch(`${API_BASE}/state`),
        fetch(`${API_BASE}/decision`),
        fetch(`${API_BASE}/timeline?limit=10`)
      ])

      if (stateRes.ok) {
        setState(await stateRes.json())
        setIsConnected(true)
        setError(null)
        setLastUpdate(new Date().toISOString())
      }

      if (decisionRes.ok) {
        setDecision(await decisionRes.json())
      }

      if (timelineRes.ok) {
        const data = await timelineRes.json()
        setTimeline(data.timeline || [])
      }

    } catch (err) {
      console.error('Failed to fetch agent data:', err)
      setIsConnected(false)
      setError('Unable to connect to Kairos Agent')
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 2000)
    return () => clearInterval(interval)
  }, [fetchData])

  return (
    <div className="app">
      <div className="background-gradient"></div>
      
      <header className="header">
        <div className="logo">
          <div className="logo-icon">
            <Icons.Clock />
          </div>
          <div className="logo-text">
            <h1>Kairos</h1>
            <span className="tagline">Autonomous Productivity Agent</span>
          </div>
        </div>
        
        <div className="privacy-badge">
          <Icons.Shield />
          <span>Privacy-first • Read-only • No surveillance</span>
        </div>
      </header>

      <ConnectionStatus isConnected={isConnected} lastUpdate={lastUpdate} />

      {error && <ErrorBanner message={error} />}

      <main className="main-content">
        <AgentStatusCard state={state} isConnected={isConnected} />
        <LastDecisionCard decision={decision} />
        <ReasoningTimeline timeline={timeline} />
      </main>

      <footer className="footer">
        <div className="footer-content">
          <p className="footer-main">
            <Icons.Shield />
            Your privacy is sacred
          </p>
          <p className="footer-sub">
            Only summarized metadata is processed • No keystrokes • No screenshots • No surveillance
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App

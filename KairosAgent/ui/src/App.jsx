/**
 * Kairos Agent UI
 * ===============
 * 
 * A minimal, ethical UI that EXPLAINS what the agent is doing.
 * 
 * CRITICAL DESIGN RULES:
 * 1. This UI is READ-ONLY - it cannot control the agent
 * 2. No productivity scores or surveillance metrics
 * 3. Focus on explaining reasoning, building trust
 * 4. Calm, non-judgmental language
 * 
 * The UI polls the local agent API and displays:
 * - Current agent state (what it thinks you're doing)
 * - Last decision (and why it was made)
 * - Reasoning timeline (transparency trail)
 */

import { useState, useEffect } from 'react'

// API base URL - proxied through Vite in dev, or direct in production
const API_BASE = '/api'

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
 * Format intent for display (human-friendly)
 */
function formatIntent(intent) {
  const labels = {
    productive: 'Focused',
    neutral: 'Neutral',
    unproductive: 'Distracted',
    unknown: 'Observing...'
  }
  return labels[intent] || intent
}

/**
 * Agent Status Card
 * Shows current state, intent, confidence
 */
function AgentStatusCard({ state, isConnected }) {
  if (!state) {
    return (
      <div className="card">
        <div className="card-title">Agent Status</div>
        <div className="loading">
          <div className="spinner"></div>
          <span>Connecting to agent...</span>
        </div>
      </div>
    )
  }

  const intentClass = `intent-${state.intent || 'unknown'}`

  return (
    <div className="card">
      <div className="card-title">Agent Status</div>
      <div className="status-card">
        <div className="status-item">
          <div className="status-label">Current Intent</div>
          <div className={`status-value ${intentClass}`}>
            {formatIntent(state.intent)}
          </div>
        </div>
        
        <div className="status-item">
          <div className="status-label">Confidence</div>
          <div className="status-value">
            {Math.round((state.confidence || 0) * 100)}%
          </div>
          <div className="confidence-bar">
            <div 
              className="confidence-fill" 
              style={{ width: `${(state.confidence || 0) * 100}%` }}
            />
          </div>
        </div>
        
        <div className="focus-context">
          <div className="label">Current Focus</div>
          <div className="value">{state.focus_context || 'Initializing...'}</div>
        </div>
      </div>
    </div>
  )
}

/**
 * Last Decision Card
 * Shows the most recent agent decision and reasoning
 */
function LastDecisionCard({ decision }) {
  if (!decision || decision.message) {
    return (
      <div className="card">
        <div className="card-title">Last Decision</div>
        <div className="empty-state">
          <div className="icon">🤔</div>
          <p>The agent hasn't made any decisions yet.</p>
          <p>It's still observing and learning your patterns.</p>
        </div>
      </div>
    )
  }

  const actionClass = decision.action === 'nudge' ? 'action-nudge' : ''

  return (
    <div className="card decision-card">
      <div className="card-title">Last Decision</div>
      
      <div className={`reasoning ${actionClass}`}>
        {decision.reasoning}
      </div>
      
      {decision.nudge_message && (
        <div className="nudge-message" style={{
          padding: '12px 16px',
          background: '#fff3cd',
          borderRadius: '8px',
          marginBottom: '12px',
          fontSize: '0.95rem'
        }}>
          💬 {decision.nudge_message}
        </div>
      )}
      
      <div className="meta">
        <span>{formatTime(decision.timestamp)}</span>
        <span className={`action-badge ${decision.action}`}>
          {decision.action === 'nudge' ? '✨ Nudged' : '👀 Observing'}
        </span>
      </div>
    </div>
  )
}

/**
 * Reasoning Timeline
 * Shows chronological history of agent decisions
 */
function ReasoningTimeline({ timeline }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="card">
        <div className="card-title">Reasoning Timeline</div>
        <div className="empty-state">
          <div className="icon">📝</div>
          <p>No reasoning history yet.</p>
          <p>Decisions will appear here as the agent makes them.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-title">Reasoning Timeline</div>
      <ul className="timeline">
        {timeline.map((item, index) => (
          <li 
            key={index} 
            className={`timeline-item ${item.action === 'nudge' ? 'action-nudge' : ''}`}
          >
            <div className="time">{formatTime(item.timestamp)}</div>
            <div className="reasoning">{item.reasoning}</div>
            <span className={`intent-tag ${item.intent}`}>
              {formatIntent(item.intent)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * Connection Status Banner
 */
function ConnectionStatus({ isConnected }) {
  return (
    <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
      <span className="status-dot"></span>
      {isConnected 
        ? 'Connected to Kairos Agent' 
        : 'Connecting to agent...'}
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

  // Poll agent API for updates
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch all data in parallel
        const [stateRes, decisionRes, timelineRes] = await Promise.all([
          fetch(`${API_BASE}/state`),
          fetch(`${API_BASE}/decision`),
          fetch(`${API_BASE}/timeline?limit=10`)
        ])

        if (stateRes.ok) {
          setState(await stateRes.json())
          setIsConnected(true)
          setError(null)
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
    }

    // Initial fetch
    fetchData()

    // Poll every 2 seconds
    const interval = setInterval(fetchData, 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="app">
      <header className="header">
        <h1>🕐 Kairos Agent</h1>
        <p className="subtitle">Your autonomous productivity companion</p>
        <div className="privacy-note">
          🔒 This UI only observes. It cannot control the agent or access your data.
        </div>
      </header>

      <ConnectionStatus isConnected={isConnected} />

      {error && (
        <div style={{
          padding: '16px',
          background: '#f8d7da',
          color: '#721c24',
          borderRadius: '8px',
          marginBottom: '20px',
          textAlign: 'center'
        }}>
          {error}
          <br />
          <small>Make sure the Kairos Agent is running.</small>
        </div>
      )}

      <AgentStatusCard state={state} isConnected={isConnected} />
      
      <LastDecisionCard decision={decision} />
      
      <ReasoningTimeline timeline={timeline} />

      <footer className="footer">
        <p>
          Kairos Agent respects your privacy. Only summarized metadata is processed.
          <br />
          No keystrokes. No screenshots. No surveillance.
        </p>
      </footer>
    </div>
  )
}

export default App

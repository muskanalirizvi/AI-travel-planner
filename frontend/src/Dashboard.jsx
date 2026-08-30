import { Link } from 'react-router-dom'
import './Dashboard.css'

const TOOLS = [
  {
    icon: '🧮',
    name: 'Calculator',
    description: 'Works out budget totals, cost splits, and other travel math.',
  },
  {
    icon: '💱',
    name: 'Currency Converter',
    description: 'Converts amounts between currencies using live exchange rates.',
  },
  {
    icon: '🌤️',
    name: 'Weather',
    description: 'Checks current weather for any city before you pack or plan.',
  },
  {
    icon: '🧠',
    name: 'Preferences Memory',
    description: 'Remembers details like your preferred airline or budget across chats.',
  },
  {
    icon: '🔎',
    name: 'Web Search',
    description: 'Looks up attractions, visa requirements, and other travel info.',
  },
  {
    icon: '🗺️',
    name: 'Distance/Maps',
    description: 'Estimates driving distance and travel time between two places.',
  },
  {
    icon: '📅',
    name: 'Calendar',
    description: 'Adds flights, hotel check-ins, and itinerary items to your calendar.',
  },
]

const STEPS = [
  'Tell the agent your travel plans.',
  'Ask it to check weather, convert currency, find distances, or save your preferences.',
  'It automatically picks the right tool for you.',
]

function Dashboard() {
  return (
    <div className="dashboard">
      <header className="dashboard-hero">
        <h1>
          <span className="title-icon" aria-hidden="true">✈️</span>
          AI Travel Planner
        </h1>
        <p>
          Plan your next trip with an AI agent that can check the weather,
          convert currencies, estimate travel times, search the web, and
          remember your preferences &mdash; all in one chat.
        </p>
        <Link to="/chat" className="start-chatting-btn">
          Start Chatting
        </Link>
      </header>

      <section className="dashboard-section">
        <h2>Available tools</h2>
        <div className="tool-grid">
          {TOOLS.map((tool) => (
            <div className="tool-card" key={tool.name}>
              <div className="tool-icon" aria-hidden="true">
                {tool.icon}
              </div>
              <div className="tool-name">{tool.name}</div>
              <div className="tool-description">{tool.description}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="dashboard-section">
        <h2>How to use</h2>
        <ol className="how-to-list">
          {STEPS.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
      </section>
    </div>
  )
}

export default Dashboard

import { Route, Routes } from 'react-router-dom'
import Dashboard from './Dashboard.jsx'
import ChatPage from './ChatPage.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/chat" element={<ChatPage />} />
    </Routes>
  )
}

export default App

import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import ComplaintList from './pages/ComplaintList';
import CreateComplaint from './pages/CreateComplaint';
import ComplaintDetail from './pages/ComplaintDetail';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <header className="header">
          <div className="container">
            <Link to="/" className="logo">
              <h1>Complaint Processor</h1>
            </Link>
            <nav>
              <Link to="/" className="nav-link">Dashboard</Link>
              <Link to="/create" className="nav-link btn-primary">+ New Complaint</Link>
            </nav>
          </div>
        </header>

        <main className="main">
          <div className="container">
            <Routes>
              <Route path="/" element={<ComplaintList />} />
              <Route path="/create" element={<CreateComplaint />} />
              <Route path="/complaints/:id" element={<ComplaintDetail />} />
            </Routes>
          </div>
        </main>

        <footer className="footer">
          <div className="container">
            <p>&copy; 2024 Complaint Processor. Powered by AI.</p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;

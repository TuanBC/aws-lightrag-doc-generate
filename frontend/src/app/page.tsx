'use client';

import ChatContainer from '@/components/chat/ChatContainer';

export default function Home() {
  return (
    <main className="app-main">
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-icon">📝</span>
            <h1>Technical Doc Generator</h1>
          </div>
          <nav className="header-nav">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="nav-link">
              GitHub
            </a>
            <a href="/api/docs" target="_blank" className="nav-link">
              API Docs
            </a>
          </nav>
        </div>
      </header>

      <div className="main-content">
        <aside className="sidebar">
          <div className="sidebar-section">
            <h3>Document Types</h3>
            <ul className="type-list">
              <li><span>📋</span> SRS</li>
              <li><span>📄</span> Functional Spec</li>
              <li><span>🔌</span> API Docs</li>
              <li><span>🏗️</span> Architecture</li>
            </ul>
          </div>

          <div className="sidebar-section">
            <h3>Features</h3>
            <ul className="feature-list">
              <li>✨ Mermaid diagrams</li>
              <li>📚 Context7 integration</li>
              <li>🔍 Knowledge base RAG</li>
              <li>✅ Auto-validation</li>
            </ul>
          </div>

          <div className="sidebar-footer">
            <p>Powered by Amazon Bedrock</p>
          </div>
        </aside>

        <section className="chat-section">
          <ChatContainer />
        </section>
      </div>
    </main>
  );
}

'use client';

import { useState } from 'react';
import ChatContainer from '@/components/chat/ChatContainer';
import { DocumentType } from '@/lib/types';
import { FileText, Database, Server, Component, Sparkles, MessageSquare, Plus, Github } from 'lucide-react';

export default function Home() {
  const [initialAction, setInitialAction] = useState<{
    type: DocumentType;
    message?: string;
    createPlan?: boolean;
  } | null>(null);

  const handleTypeSelect = (type: DocumentType) => {
    setInitialAction({ type });
    setTimeout(() => setInitialAction(null), 100);
  };

  return (
    <main className="app-main">
      <aside className="sidebar">
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={() => window.location.reload()}>
            <Plus size={20} />
            <span>New document</span>
          </button>
        </div>

        <div className="sidebar-section">
          <h3>Templates</h3>
          <ul className="nav-list">
            <li onClick={() => handleTypeSelect(DocumentType.SRS)} className="nav-item">
              <FileText size={18} /> <span>SRS</span>
            </li>
            <li onClick={() => handleTypeSelect(DocumentType.FUNCTIONAL_SPEC)} className="nav-item">
              <Database size={18} /> <span>Functional Spec</span>
            </li>
            <li onClick={() => handleTypeSelect(DocumentType.API_DOCS)} className="nav-item">
              <Server size={18} /> <span>API Docs</span>
            </li>
            <li onClick={() => handleTypeSelect(DocumentType.ARCHITECTURE)} className="nav-item">
              <Component size={18} /> <span>Architecture</span>
            </li>
            <li onClick={() => handleTypeSelect(DocumentType.GENERAL)} className="nav-item">
              <Sparkles size={18} /> <span>General</span>
            </li>
          </ul>
        </div>

        <div className="sidebar-footer">
          <a href="https://github.com" target="_blank" className="nav-link-footer">
            <Github size={16} /> GitHub
          </a>
          <div className="powered-by">Powered by Bedrock</div>
        </div>
      </aside>

      <section className="main-view">
        <header className="mobile-header">
          <h1>Tech Docs</h1>
        </header>
        <ChatContainer initialAction={initialAction} />
      </section>
    </main>
  );
}

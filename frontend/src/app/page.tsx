'use client';

import { useState } from 'react';
import ChatContainer from '@/components/chat/ChatContainer';
import { Sparkles } from 'lucide-react';

export default function Home() {
  return (
    <main className="microsite">
      {/* Header */}
      <header className="microsite-header">
        <div className="logo">
          <Sparkles size={28} />
          <h1>DocGen AI</h1>
        </div>
        <p className="tagline">Generate technical documentation from your code</p>
      </header>

      {/* Chat Area */}
      <div className="chat-wrapper">
        <ChatContainer />
      </div>
    </main>
  );
}

import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, FileText, Send, Trash2, Bot, User, Loader2, Sparkles } from 'lucide-react';

const API_BASE = 'https://notebookllm-0n6y.onrender.com/api/v1';

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [rawText, setRawText] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  
  const [isUploading, setIsUploading] = useState(false);
  const [isChatting, setIsChatting] = useState(false);
  const [error, setError] = useState('');

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });
      
      if (!res.ok) throw new Error(await res.text());
      
      const data = await res.json();
      setSessionId(data.session_id);
      setMessages([{ role: 'assistant', content: 'Document successfully indexed! What would you like to know about it?' }]);
      setSelectedFile(null);
      if(fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setError('Failed to upload document. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleTextUpload = async (e) => {
    e.preventDefault();
    if (!rawText.trim()) return;

    setIsUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('text', rawText);

    try {
      const res = await fetch(`${API_BASE}/upload-text`, {
        method: 'POST',
        body: formData,
      });
      
      if (!res.ok) throw new Error(await res.text());
      
      const data = await res.json();
      setSessionId(data.session_id);
      setMessages([{ role: 'assistant', content: 'Text successfully indexed! Ask me anything about it.' }]);
      setRawText('');
    } catch (err) {
      setError('Failed to process text. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || !sessionId || isChatting) return;

    const userMsg = inputValue.trim();
    setInputValue('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsChatting(true);
    setError('');

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, query: userMsg }),
      });

      if (!res.ok) throw new Error('Chat request failed');

      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
    } finally {
      setIsChatting(false);
    }
  };

  const handleClearSession = async () => {
    if (!sessionId) return;
    try {
      await fetch(`${API_BASE}/session/${sessionId}`, { method: 'DELETE' });
    } catch (e) {
      console.error(e);
    }
    setSessionId(null);
    setMessages([]);
    setError('');
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans text-slate-900 overflow-hidden">
      
      {/* SIDEBAR: Upload Controls */}
      <aside className="w-96 bg-white border-r border-slate-200 flex flex-col shadow-sm z-10">
        <div className="p-6 border-b border-slate-100 flex items-center gap-3">
          <div className="bg-teal-100 p-2 rounded-lg text-teal-600">
            <Sparkles size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800 tracking-tight cursor-pointer">NotebookRAG</h1>
            <p className="text-xs text-slate-500 font-medium">Context-Aware AI Assistant</p>
          </div>
        </div>

        <div className="p-6 flex-1 overflow-y-auto space-y-8">
          {error && (
            <div className="p-3 bg-red-50 text-red-600 border border-red-200 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* Upload File Section */}
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
              <UploadCloud size={16} /> Upload Document
            </h2>
            <form onSubmit={handleFileUpload} className="space-y-3">
              <input 
                type="file" 
                accept=".pdf,.txt,.csv"
                ref={fileInputRef}
                onChange={(e) => setSelectedFile(e.target.files[0])}
                className="block w-full text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-teal-50 file:text-teal-700 hover:file:bg-teal-100 transition-colors cursor-pointer border border-slate-200 rounded-lg"
                disabled={isUploading || sessionId}
              />
              <button 
                type="submit" 
                disabled={!selectedFile || isUploading || sessionId}
                className="w-full py-2.5 bg-slate-800 text-white rounded-lg font-medium hover:bg-slate-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors cursor-pointer flex justify-center items-center gap-2"
              >
                {isUploading ? <Loader2 size={18} className="animate-spin" /> : 'Index File'}
              </button>
            </form>
          </section>

          <div className="flex items-center gap-4">
            <div className="h-px bg-slate-200 flex-1"></div>
            <span className="text-xs text-slate-400 font-medium uppercase">OR</span>
            <div className="h-px bg-slate-200 flex-1"></div>
          </div>

          {/* Upload Text Section */}
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
              <FileText size={16} /> Paste Raw Text
            </h2>
            <form onSubmit={handleTextUpload} className="space-y-3">
              <textarea 
                rows="4" 
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="Paste your notes or document text here..."
                className="w-full p-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none resize-none"
                disabled={isUploading || sessionId}
              />
              <button 
                type="submit" 
                disabled={!rawText.trim() || isUploading || sessionId}
                className="w-full py-2.5 bg-slate-800 text-white rounded-lg font-medium hover:bg-slate-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors cursor-pointer flex justify-center items-center gap-2"
              >
                {isUploading ? <Loader2 size={18} className="animate-spin" /> : 'Index Text'}
              </button>
            </form>
          </section>
        </div>

        {/* Session Status Footer */}
        <div className="p-6 border-t border-slate-100 bg-slate-50/50">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-slate-600">Session Status</span>
            <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${sessionId ? 'bg-teal-100 text-teal-700' : 'bg-slate-200 text-slate-600'}`}>
              {sessionId ? 'Active' : 'Inactive'}
            </span>
          </div>
          <button 
            onClick={handleClearSession}
            disabled={!sessionId}
            className="w-full py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer flex items-center justify-center gap-2"
          >
            <Trash2 size={16} /> Clear Workspace
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT: Chat Interface */}
      <main className="flex-1 flex flex-col bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] bg-slate-50/90 bg-blend-overlay">
        
        {/* Chat History */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6">
          {!sessionId && messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
              <div className="w-20 h-20 bg-teal-100 text-teal-500 rounded-2xl flex items-center justify-center mb-6 shadow-sm border border-teal-200">
                <Sparkles size={40} />
              </div>
              <h2 className="text-2xl font-bold text-slate-800 mb-2">Ready to Learn</h2>
              <p className="text-slate-500 leading-relaxed">
                Upload a PDF, TXT or CSV file or paste text in the sidebar to create a grounded context. The AI will strictly use your document to answer questions.
              </p>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center text-white shrink-0 mt-1 shadow-sm">
                      <Bot size={18} />
                    </div>
                  )}
                  
                  <div className={`px-5 py-3.5 rounded-2xl max-w-[80%] leading-relaxed shadow-sm ${
                    msg.role === 'user' 
                      ? 'bg-slate-800 text-white rounded-br-none' 
                      : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none'
                  }`}>
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>

                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 shrink-0 mt-1 shadow-sm">
                      <User size={18} />
                    </div>
                  )}
                </div>
              ))}
              
              {isChatting && (
                <div className="flex gap-4 justify-start">
                  <div className="w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center text-white shrink-0 mt-1 shadow-sm">
                    <Bot size={18} />
                  </div>
                  <div className="px-5 py-4 rounded-2xl bg-white border border-slate-200 rounded-bl-none shadow-sm flex items-center gap-2">
                    <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                    <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Chat Input */}
        <div className="p-6 bg-white border-t border-slate-200">
          <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto relative">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={sessionId ? "Ask a question about your document..." : "Upload a document to start asking questions..."}
              disabled={!sessionId || isChatting}
              className="w-full pl-5 pr-14 py-4 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none disabled:opacity-60 disabled:bg-slate-100 shadow-sm transition-all"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || !sessionId || isChatting}
              className="absolute right-2 top-2 bottom-2 aspect-square bg-teal-600 text-white rounded-lg flex items-center justify-center hover:bg-teal-700 disabled:bg-slate-300 disabled:text-slate-500 transition-colors cursor-pointer"
            >
              <Send size={18} className="ml-1" />
            </button>
          </form>
          <div className="max-w-4xl mx-auto mt-2 flex justify-center gap-4">
              <span className="text-xs text-slate-400 font-medium tracking-wide">Responses grounded strictly in document context</span>
          </div>
        </div>

      </main>
    </div>
  );
}
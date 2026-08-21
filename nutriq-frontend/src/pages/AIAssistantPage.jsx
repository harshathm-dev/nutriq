import React, { useState, useRef, useEffect } from 'react';
import { api } from '../services/api';
import { useStore } from '../store/useStore';
import {
  Sparkles, Send, User, Bot, AlertCircle, Plus,
  MessageSquare, Trash2, Edit3, MoreVertical, Search,
  X, ChevronRight, ChevronLeft, History, RotateCcw,
  Check, Clock
} from 'lucide-react';

const PREDEFINED_CATEGORIES = [
  {
    name: 'CALORIES',
    questions: [
      "How many calories do I have left?",
      "Am I within my calorie goal?",
      "How many calories should dinner have?"
    ]
  },
  {
    name: 'PROTEIN',
    questions: [
      "How much protein do I still need?",
      "Suggest a high-protein dinner.",
      "What are good vegetarian protein sources?"
    ]
  },
  {
    name: 'WEIGHT LOSS',
    questions: [
      "Is my current calorie intake suitable for weight loss?",
      "Am I progressing toward my goal?",
      "What should I eat for weight loss?"
    ]
  },
  {
    name: 'INDIAN FOOD',
    questions: [
      "Can I eat dosa for dinner?",
      "Is white rice okay for weight loss?",
      "How many calories are in idli?"
    ]
  },
  {
    name: 'MEAL SUGGESTIONS',
    questions: [
      "Suggest breakfast.",
      "Suggest lunch.",
      "Suggest dinner.",
      "Give me a meal under 400 calories."
    ]
  },
  {
    name: 'PROGRESS',
    questions: [
      "How did I do today?",
      "How is my weekly progress?",
      "What should I improve?"
    ]
  },
  {
    name: 'WATER',
    questions: [
      "How much water should I drink?",
      "How much water have I consumed?"
    ]
  }
];

const FormattedMessage = ({ content, isUser }) => {
  if (isUser) {
    return <span>{content}</span>;
  }

  const parseInline = (text) => {
    const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} style={{ color: 'inherit', fontWeight: '800' }}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('*') && part.endsWith('*')) {
        return <em key={i} style={{ opacity: 0.85, fontStyle: 'italic' }}>{part.slice(1, -1)}</em>;
      }
      return part;
    });
  };

  const lines = (content || '').split('\n');
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={idx} style={{ height: '4px' }} />;
        if (trimmed.startsWith('### ')) {
          return (
            <div key={idx} style={{ fontSize: '0.98rem', fontWeight: '800', color: '#1D4ED8', marginTop: '4px' }}>
              {parseInline(trimmed.replace(/^###\s+/, ''))}
            </div>
          );
        }
        if (trimmed.startsWith('## ')) {
          return (
            <div key={idx} style={{ fontSize: '1.05rem', fontWeight: '800', color: '#1E40AF', marginTop: '6px' }}>
              {parseInline(trimmed.replace(/^##\s+/, ''))}
            </div>
          );
        }
        if (trimmed.startsWith('• ') || trimmed.startsWith('- ') || (trimmed.startsWith('* ') && !trimmed.startsWith('** '))) {
          const bulletContent = trimmed.replace(/^[•\-\*]\s+/, '');
          return (
            <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', paddingLeft: '4px' }}>
              <span style={{ color: '#2563EB', fontSize: '1.1rem', lineHeight: '1.2' }}>•</span>
              <span style={{ flex: 1 }}>{parseInline(bulletContent)}</span>
            </div>
          );
        }
        return <div key={idx}>{parseInline(line)}</div>;
      })}
    </div>
  );
};

export const AIAssistantPage = () => {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [activeConversationTitle, setActiveConversationTitle] = useState('New Conversation');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCategoryIndex, setSelectedCategoryIndex] = useState(0);

  // Chat History Sidebar State
  const [isHistoryOpen, setIsHistoryOpen] = useState(true);
  const [historySearchQuery, setHistorySearchQuery] = useState('');

  // Modal States for Rename & Delete
  const [renamingId, setRenamingId] = useState(null);
  const [renameInput, setRenameInput] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  const messagesEndRef = useRef(null);
  const lastFailedPromptRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Load conversations on mount
  useEffect(() => {
    loadConversationsAndActive();
  }, []);

  const loadConversationsAndActive = async () => {
    setIsLoadingMessages(true);
    setError(null);
    try {
      const convList = await api.getConversations();
      setConversations(convList || []);

      if (convList && convList.length > 0) {
        // Select the most recently updated conversation
        const latest = convList[0];
        await selectConversation(latest.id, latest.title);
      } else {
        // Initialize fresh conversation
        await startNewChat();
      }
    } catch (e) {
      console.error("NutriQ AI request failed while loading conversations:", e);
      setMessages([
        {
          role: 'assistant',
          content: "Hello! I am **NutriQ AI**, your personal nutrition companion. How can I assist you with your diet and macros today?"
        }
      ]);
    } finally {
      setIsLoadingMessages(false);
    }
  };

  const selectConversation = async (conversationId, title = null) => {
    if (!conversationId) return;
    setActiveConversationId(conversationId);
    if (title) setActiveConversationTitle(title);
    setError(null);
    setIsLoadingMessages(true);

    try {
      const detail = await api.getConversation(conversationId);
      if (detail) {
        setActiveConversationTitle(detail.title || 'New Conversation');
        if (detail.messages && detail.messages.length > 0) {
          setMessages(detail.messages.map(m => ({
            id: m.id || m.messageId,
            role: m.role,
            content: m.content,
            timestamp: m.created_at || m.timestamp
          })));
        } else {
          setMessages([
            {
              role: 'assistant',
              content: "Hello! I am **NutriQ AI**, your personal nutrition companion. What questions can I answer about your meals, macros, or wellness goals today?"
            }
          ]);
        }
      }
    } catch (e) {
      console.error("NutriQ AI request failed while fetching conversation detail:", e);
      setError("Unable to load previous messages for this conversation.");
    } finally {
      setIsLoadingMessages(false);
    }
  };

  const startNewChat = async () => {
    setError(null);
    try {
      const newConv = await api.createConversation("New Conversation");
      const convId = newConv.id || newConv.conversationId;
      setActiveConversationId(convId);
      setActiveConversationTitle("New Conversation");
      setMessages([
        {
          role: 'assistant',
          content: "Hello! I am **NutriQ AI**, your personal nutrition companion powered by Gemini. I have full context on your daily targets, logged meals, calorie budget, and verified Indian nutrition. How can I help you today?"
        }
      ]);
      const updatedList = await api.getConversations();
      setConversations(updatedList || []);
    } catch (e) {
      console.error("NutriQ AI request failed while starting new chat:", e);
    }
  };

  const handleSendMessage = async (promptText = null, isRetry = false) => {
    const textToSend = promptText || input.trim();
    if (!textToSend || isStreaming) return;

    if (!isRetry) {
      setInput('');
    }
    setError(null);
    lastFailedPromptRef.current = textToSend;

    // Ensure we have an active conversation
    let targetConvId = activeConversationId;
    if (!targetConvId) {
      try {
        const created = await api.createConversation("New Conversation");
        targetConvId = created.id || created.conversationId;
        setActiveConversationId(targetConvId);
      } catch (e) {
        console.error("NutriQ AI request failed creating conversation:", e);
      }
    }

    // Set messages depending on retry vs new message
    if (isRetry) {
      // If retrying, remove the last error assistant message and replace with thinking placeholder
      setMessages(prev => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
          updated[lastIdx] = { role: 'assistant', content: '', isThinking: true };
          return updated;
        }
        return [...updated, { role: 'assistant', content: '', isThinking: true }];
      });
    } else {
      const userMsg = { role: 'user', content: textToSend, timestamp: new Date().toISOString() };
      const tempAssistantMsg = { role: 'assistant', content: '', isThinking: true };
      setMessages(prev => [...prev, userMsg, tempAssistantMsg]);
    }

    setIsStreaming(true);

    try {
      let accumulatedText = '';
      await api.sendConversationMessage({
        conversationId: targetConvId,
        content: textToSend,
        stream: true,
        onChunk: (chunk) => {
          accumulatedText += chunk;
          setMessages(prev => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = {
                role: 'assistant',
                content: accumulatedText,
                isThinking: false
              };
            }
            return updated;
          });
        },
        onDone: (metadata, messageId) => {
          // Refresh conversations to update titles and ordering
          api.getConversations().then(res => {
            setConversations(res || []);
            const current = (res || []).find(c => c.id === targetConvId);
            if (current && current.title) {
              setActiveConversationTitle(current.title);
            }
          }).catch(err => {
            console.error("NutriQ AI request failed fetching conversations on done:", err);
          });
        }
      });
    } catch (err) {
      console.error("NutriQ AI request failed:", err);
      
      // Determine descriptive, user-friendly error message
      let errorMessage = "NutriQ AI is temporarily unavailable. Please try again.";
      if (err?.status === 401) {
        errorMessage = "Your session has expired. Please log in again.";
      } else if (err?.status === 404) {
        errorMessage = "Conversation not found. Starting a new chat.";
      } else if (err?.status === 422) {
        errorMessage = "NutriQ AI received invalid request data.";
      } else if (err?.status === 429) {
        errorMessage = "AI service is temporarily rate-limited. Please try again shortly.";
      } else if (err?.status >= 500) {
        errorMessage = "NutriQ AI encountered a server error. Please retry.";
      } else if (err?.message && (err.message.includes("Failed to fetch") || err.message.includes("NetworkError") || err.message.includes("network"))) {
        errorMessage = "Unable to connect to NutriQ AI. Check that the backend is running.";
      } else if (err?.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);
      setMessages(prev => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
          updated[lastIdx] = {
            role: 'assistant',
            content: errorMessage,
            isThinking: false,
            isError: true
          };
        }
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const handleRetry = () => {
    if (lastFailedPromptRef.current) {
      handleSendMessage(lastFailedPromptRef.current, true);
    }
  };

  const handleConfirmRename = async () => {
    if (!renamingId || !renameInput.trim()) {
      setRenamingId(null);
      return;
    }
    try {
      await api.renameConversation(renamingId, renameInput.trim());
      if (activeConversationId === renamingId) {
        setActiveConversationTitle(renameInput.trim());
      }
      const updatedList = await api.getConversations();
      setConversations(updatedList || []);
    } catch (e) {
      console.error("NutriQ AI request failed renaming conversation:", e);
    } finally {
      setRenamingId(null);
      setRenameInput('');
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletingId) return;
    try {
      await api.deleteConversation(deletingId);
      const updatedList = await api.getConversations();
      setConversations(updatedList || []);

      if (activeConversationId === deletingId) {
        if (updatedList && updatedList.length > 0) {
          await selectConversation(updatedList[0].id, updatedList[0].title);
        } else {
          await startNewChat();
        }
      }
    } catch (e) {
      console.error("NutriQ AI request failed deleting conversation:", e);
    } finally {
      setDeletingId(null);
    }
  };

  // Group conversations by Today, Yesterday, Previous 7 Days, Older
  const groupConversations = () => {
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const yesterdayStart = todayStart - 86400000;
    const sevenDaysAgoStart = todayStart - 6 * 86400000;

    const filtered = (conversations || []).filter(c => {
      if (!historySearchQuery.trim()) return true;
      const q = historySearchQuery.toLowerCase();
      const titleMatch = (c.title || '').toLowerCase().includes(q);
      const previewMatch = (c.last_message_preview || '').toLowerCase().includes(q);
      return titleMatch || previewMatch;
    });

    const groups = {
      today: [],
      yesterday: [],
      previous7Days: [],
      older: []
    };

    filtered.forEach((conv) => {
      const time = new Date(conv.updated_at || conv.updatedAt || conv.created_at || conv.createdAt).getTime();
      if (time >= todayStart) {
        groups.today.push(conv);
      } else if (time >= yesterdayStart) {
        groups.yesterday.push(conv);
      } else if (time >= sevenDaysAgoStart) {
        groups.previous7Days.push(conv);
      } else {
        groups.older.push(conv);
      }
    });

    return groups;
  };

  const formatTimestamp = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const time = d.getTime();

    if (time >= todayStart) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    }
    if (time >= todayStart - 86400000) {
      return 'Yesterday';
    }
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const grouped = groupConversations();
  const activeCategory = PREDEFINED_CATEGORIES[selectedCategoryIndex];

  return (
    <div className="page-container" style={{ height: 'calc(100vh - 110px)', paddingBottom: 0, display: 'flex', flexDirection: 'column' }}>
      
      {/* 1. Header Banner */}
      <div className="wellness-card" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0, gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            background: '#2563EB',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(37, 99, 235, 0.25)'
          }}>
            <Sparkles size={20} color="#FFFFFF" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                NutriQ AI
              </h2>
              <span style={{
                fontSize: '0.66rem',
                padding: '2px 8px',
                borderRadius: '9999px',
                background: '#EFF6FF',
                color: '#1D4ED8',
                border: '1px solid #BFDBFE',
                fontWeight: '700'
              }}>
                Powered by Gemini
              </span>
            </div>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
              Personal Nutrition & Diet Intelligence
            </span>
          </div>
        </div>

        {/* Action Controls: Chat History Toggle & + New Chat */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            onClick={() => setIsHistoryOpen(!isHistoryOpen)}
            style={{
              padding: '7px 14px',
              fontSize: '0.82rem',
              borderRadius: 'var(--radius-md, 8px)',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: isHistoryOpen ? '#EFF6FF' : 'var(--bg-card, #FFFFFF)',
              color: isHistoryOpen ? '#1D4ED8' : 'var(--text-secondary)',
              border: isHistoryOpen ? '1px solid #BFDBFE' : '1px solid var(--border-glass)',
              transition: 'all 0.14s ease'
            }}
            title="Toggle Chat History panel"
          >
            <History size={15} color={isHistoryOpen ? '#2563EB' : 'currentColor'} />
            <span>Chat History</span>
            {conversations.length > 0 && (
              <span style={{
                background: isHistoryOpen ? '#2563EB' : 'var(--bg-subtle, #EEF4F0)',
                color: isHistoryOpen ? '#FFFFFF' : 'var(--text-secondary)',
                borderRadius: '10px',
                padding: '1px 6px',
                fontSize: '0.7rem',
                fontWeight: '700'
              }}>
                {conversations.length}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={startNewChat}
            style={{
              padding: '7px 15px',
              fontSize: '0.82rem',
              gap: '6px',
              display: 'flex',
              alignItems: 'center',
              borderRadius: 'var(--radius-md, 8px)',
              background: '#2563EB',
              color: '#FFFFFF',
              border: 'none',
              fontWeight: '700',
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(37, 99, 235, 0.25)',
              transition: 'background 0.14s ease'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#1D4ED8'}
            onMouseLeave={(e) => e.currentTarget.style.background = '#2563EB'}
          >
            <Plus size={16} />
            <span>New Chat</span>
          </button>
        </div>
      </div>

      {/* 2. Main Body Container: Chat History Left Panel + Current Conversation Right Panel */}
      <div style={{ flex: 1, display: 'flex', gap: '16px', marginTop: '14px', minHeight: 0, position: 'relative' }}>
        
        {/* LEFT PANEL: Chat History Sidebar */}
        {isHistoryOpen && (
          <div
            className="wellness-card"
            style={{
              width: '300px',
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              padding: '14px',
              overflow: 'hidden',
              background: 'var(--bg-card, #FFFFFF)',
              borderRadius: 'var(--radius-lg, 16px)'
            }}
          >
            {/* History Header & Search */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <History size={16} color="#2563EB" />
                <span style={{ fontSize: '0.88rem', fontWeight: '800', color: 'var(--text-primary)' }}>
                  Chat History
                </span>
              </div>
              <button
                type="button"
                onClick={startNewChat}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#2563EB',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center'
                }}
                title="Start new conversation"
              >
                <Plus size={16} />
              </button>
            </div>

            {/* Internal History Search Bar */}
            <div style={{ position: 'relative', marginBottom: '12px' }}>
              <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                placeholder="Search conversations..."
                value={historySearchQuery}
                onChange={(e) => setHistorySearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  paddingLeft: '32px',
                  paddingRight: historySearchQuery ? '26px' : '10px',
                  height: '32px',
                  fontSize: '0.78rem',
                  borderRadius: 'var(--radius-md, 8px)',
                  border: '1px solid var(--border-glass)',
                  background: 'var(--bg-subtle, #EEF4F0)',
                  outline: 'none'
                }}
              />
              {historySearchQuery && (
                <button
                  type="button"
                  onClick={() => setHistorySearchQuery('')}
                  style={{
                    position: 'absolute',
                    right: '6px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    fontSize: '0.75rem'
                  }}
                >
                  ✕
                </button>
              )}
            </div>

            {/* Conversation Group List (Scrollable) */}
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px', paddingRight: '2px' }}>
              {conversations.length === 0 ? (
                /* Empty State */
                <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--text-secondary)' }}>
                  <MessageSquare size={28} color="var(--text-muted)" style={{ margin: '0 auto 8px auto', opacity: 0.6 }} />
                  <div style={{ fontSize: '0.84rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                    No conversations yet
                  </div>
                  <p style={{ fontSize: '0.74rem', margin: '4px 0 12px 0' }}>
                    Start a conversation with NutriQ AI to see your history here.
                  </p>
                  <button
                    type="button"
                    onClick={startNewChat}
                    style={{
                      padding: '6px 12px',
                      fontSize: '0.76rem',
                      margin: '0 auto',
                      borderRadius: 'var(--radius-md, 8px)',
                      background: '#2563EB',
                      color: '#FFFFFF',
                      border: 'none',
                      fontWeight: '700',
                      cursor: 'pointer'
                    }}
                  >
                    + New Chat
                  </button>
                </div>
              ) : (
                <>
                  {/* TODAY GROUP */}
                  {grouped.today.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.68rem', fontWeight: '800', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px', paddingLeft: '4px' }}>
                        Today
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {grouped.today.map(c => renderHistoryItem(c))}
                      </div>
                    </div>
                  )}

                  {/* YESTERDAY GROUP */}
                  {grouped.yesterday.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.68rem', fontWeight: '800', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px', paddingLeft: '4px' }}>
                        Yesterday
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {grouped.yesterday.map(c => renderHistoryItem(c))}
                      </div>
                    </div>
                  )}

                  {/* PREVIOUS 7 DAYS GROUP */}
                  {grouped.previous7Days.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.68rem', fontWeight: '800', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px', paddingLeft: '4px' }}>
                        Previous 7 Days
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {grouped.previous7Days.map(c => renderHistoryItem(c))}
                      </div>
                    </div>
                  )}

                  {/* OLDER GROUP */}
                  {grouped.older.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.68rem', fontWeight: '800', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px', paddingLeft: '4px' }}>
                        Older
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {grouped.older.map(c => renderHistoryItem(c))}
                      </div>
                    </div>
                  )}

                  {/* No search matches */}
                  {grouped.today.length === 0 && grouped.yesterday.length === 0 && grouped.previous7Days.length === 0 && grouped.older.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '24px 10px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      No conversations match "{historySearchQuery}"
                    </div>
                  )}
                </>
              )}
            </div>

          </div>
        )}

        {/* RIGHT PANEL: Active Conversation Chat Area */}
        <div
          className="wellness-card"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            minHeight: 0,
            background: 'var(--bg-card, #FFFFFF)',
            borderRadius: 'var(--radius-lg, 16px)'
          }}
        >
          
          {/* Active Conversation Sub-header */}
          <div style={{
            padding: '10px 18px',
            borderBottom: '1px solid var(--border-glass)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-subtle, #EEF4F0)',
            flexShrink: 0
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
              <MessageSquare size={16} color="#2563EB" />
              <span style={{ fontSize: '0.88rem', fontWeight: '800', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {activeConversationTitle}
              </span>
            </div>

            {/* Quick Rename / Info */}
            <button
              type="button"
              onClick={() => {
                if (activeConversationId) {
                  setRenamingId(activeConversationId);
                  setRenameInput(activeConversationTitle);
                }
              }}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-secondary)',
                fontSize: '0.74rem',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '3px 8px',
                borderRadius: 'var(--radius-sm, 6px)'
              }}
              title="Rename conversation"
            >
              <Edit3 size={13} />
              <span>Rename</span>
            </button>
          </div>

          {/* Messages Scroll View */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {isLoadingMessages ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-secondary)' }}>
                <div className="animate-spin" style={{ display: 'inline-block', fontSize: '1.4rem', marginBottom: '8px' }}>✨</div>
                <div style={{ fontSize: '0.86rem' }}>Loading conversation messages...</div>
              </div>
            ) : (
              messages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                return (
                  <div
                    key={msg.id || idx}
                    style={{
                      display: 'flex',
                      justifyContent: isUser ? 'flex-end' : 'flex-start',
                      gap: '10px',
                      maxWidth: '100%'
                    }}
                  >
                    {!isUser && (
                      <div style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '50%',
                        background: '#2563EB',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#FFFFFF',
                        flexShrink: 0,
                        boxShadow: '0 2px 6px rgba(37, 99, 235, 0.2)'
                      }}>
                        <Bot size={18} />
                      </div>
                    )}

                    <div
                      style={{
                        maxWidth: '82%',
                        padding: '12px 16px',
                        borderRadius: 'var(--radius-lg, 16px)',
                        background: isUser ? '#2563EB' : '#EFF6FF',
                        color: isUser ? '#FFFFFF' : '#0F172A',
                        border: isUser ? '1px solid #2563EB' : '1px solid #BFDBFE',
                        fontSize: '0.9rem',
                        lineHeight: '1.5',
                        boxShadow: 'var(--shadow-sm)'
                      }}
                    >
                      {msg.isThinking ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#1D4ED8' }}>
                          <span className="animate-spin" style={{ display: 'inline-block' }}>✨</span>
                          <span>NutriQ AI is analyzing...</span>
                        </div>
                      ) : (
                        <>
                          <FormattedMessage content={msg.content} isUser={isUser} />
                          {msg.timestamp && (
                            <div style={{
                              fontSize: '0.68rem',
                              color: isUser ? 'rgba(255, 255, 255, 0.8)' : 'var(--text-muted)',
                              marginTop: '6px',
                              textAlign: isUser ? 'right' : 'left'
                            }}>
                              {formatTimestamp(msg.timestamp)}
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {isUser && (
                      <div style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '50%',
                        background: '#EFF6FF',
                        border: '1px solid #BFDBFE',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#1D4ED8',
                        fontWeight: '800',
                        fontSize: '0.78rem',
                        flexShrink: 0
                      }}>
                        <User size={16} />
                      </div>
                    )}
                  </div>
                );
              })
            )}
            
            {/* Error retry banner */}
            {error && (
              <div style={{
                padding: '10px 14px',
                borderRadius: 'var(--radius-md, 8px)',
                background: 'var(--error-bg, #FDE8E8)',
                color: 'var(--error, #DC4C4C)',
                fontSize: '0.82rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertCircle size={15} />
                  <span>{error}</span>
                </div>
                <button
                  type="button"
                  onClick={handleRetry}
                  style={{
                    background: 'none',
                    border: '1px solid var(--error, #DC4C4C)',
                    color: 'var(--error, #DC4C4C)',
                    padding: '3px 8px',
                    borderRadius: 'var(--radius-sm, 6px)',
                    cursor: 'pointer',
                    fontSize: '0.74rem',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <RotateCcw size={12} /> Retry
                </button>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* 3. Suggested Smart Question Categories & Prompts */}
          <div style={{ borderTop: '1px solid var(--border-glass)', background: 'var(--bg-subtle, #EEF4F0)' }}>
            {/* Category Tab Bar */}
            <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', padding: '8px 16px 4px 16px' }}>
              {PREDEFINED_CATEGORIES.map((cat, idx) => {
                const isSelected = selectedCategoryIndex === idx;
                return (
                  <button
                    key={cat.name}
                    type="button"
                    onClick={() => setSelectedCategoryIndex(idx)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: 'var(--radius-full)',
                      border: isSelected ? '1px solid #2563EB' : '1px solid #BFDBFE',
                      background: isSelected ? '#2563EB' : '#EFF6FF',
                      color: isSelected ? '#FFFFFF' : '#1D4ED8',
                      fontSize: '0.7rem',
                      fontWeight: '700',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                      boxShadow: isSelected ? '0 2px 8px rgba(37, 99, 235, 0.25)' : 'none',
                      transition: 'all 0.14s ease'
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.background = '#DBEAFE';
                        e.currentTarget.style.borderColor = '#60A5FA';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.background = '#EFF6FF';
                        e.currentTarget.style.borderColor = '#BFDBFE';
                      }
                    }}
                  >
                    {cat.name}
                  </button>
                );
              })}
            </div>

            {/* Prompt Chips */}
            <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', padding: '4px 16px 8px 16px' }}>
              {activeCategory.questions.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSendMessage(q)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-full)',
                    background: '#FFFFFF',
                    border: '1px solid #BFDBFE',
                    color: '#1D4ED8',
                    fontSize: '0.74rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.14s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#2563EB';
                    e.currentTarget.style.background = '#EFF6FF';
                    e.currentTarget.style.color = '#2563EB';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#BFDBFE';
                    e.currentTarget.style.background = '#FFFFFF';
                    e.currentTarget.style.color = '#1D4ED8';
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* 4. Chat Input Form */}
          <form
            onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}
            style={{ padding: '12px 18px', background: 'var(--bg-card, #FFFFFF)', borderTop: '1px solid var(--border-glass)', display: 'flex', gap: '10px' }}
          >
            <input
              type="text"
              className="input-field"
              placeholder="Ask NutriQ AI about calories, macros, recipes, or weight progress..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isStreaming}
              style={{ height: '44px', fontSize: '0.9rem' }}
            />
            <button
              type="submit"
              disabled={!input.trim() || isStreaming}
              style={{
                padding: '0 20px',
                height: '44px',
                flexShrink: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 'var(--radius-md, 8px)',
                background: !input.trim() || isStreaming ? '#93C5FD' : '#2563EB',
                color: '#FFFFFF',
                border: 'none',
                cursor: !input.trim() || isStreaming ? 'not-allowed' : 'pointer',
                boxShadow: !input.trim() || isStreaming ? 'none' : '0 2px 8px rgba(37, 99, 235, 0.25)',
                transition: 'background 0.14s ease'
              }}
              onMouseEnter={(e) => {
                if (input.trim() && !isStreaming) {
                  e.currentTarget.style.background = '#1D4ED8';
                }
              }}
              onMouseLeave={(e) => {
                if (input.trim() && !isStreaming) {
                  e.currentTarget.style.background = '#2563EB';
                }
              }}
            >
              <Send size={16} />
            </button>
          </form>

        </div>

      </div>

      {/* RENAME MODAL DIALOG */}
      {renamingId && (
        <div className="modal-overlay" onClick={() => setRenamingId(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '420px', padding: '20px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '800', margin: '0 0 12px 0', color: 'var(--text-primary)' }}>
              Rename Conversation
            </h3>
            <input
              type="text"
              className="input-field"
              value={renameInput}
              onChange={(e) => setRenameInput(e.target.value)}
              placeholder="Enter new conversation title..."
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleConfirmRename();
                if (e.key === 'Escape') setRenamingId(null);
              }}
              style={{ marginBottom: '16px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setRenamingId(null)}
                className="btn-secondary"
                style={{ padding: '7px 14px', fontSize: '0.84rem' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmRename}
                style={{
                  padding: '7px 14px',
                  fontSize: '0.84rem',
                  borderRadius: 'var(--radius-md, 8px)',
                  background: '#2563EB',
                  color: '#FFFFFF',
                  border: 'none',
                  fontWeight: '700',
                  cursor: 'pointer'
                }}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL DIALOG */}
      {deletingId && (
        <div className="modal-overlay" onClick={() => setDeletingId(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '400px', padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--error, #DC4C4C)', marginBottom: '10px' }}>
              <AlertCircle size={22} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                Delete this conversation?
              </h3>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '0 0 18px 0', lineHeight: 1.5 }}>
              This will permanently delete this conversation and all its messages. This action cannot be undone.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setDeletingId(null)}
                className="btn-secondary"
                style={{ padding: '7px 14px', fontSize: '0.84rem' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                style={{
                  padding: '7px 16px',
                  borderRadius: 'var(--radius-md, 8px)',
                  background: 'var(--error, #DC4C4C)',
                  color: '#FFFFFF',
                  border: 'none',
                  fontWeight: '700',
                  fontSize: '0.84rem',
                  cursor: 'pointer'
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );

  function renderHistoryItem(conv) {
    const isSelected = activeConversationId === conv.id;
    return (
      <div
        key={conv.id}
        onClick={() => selectConversation(conv.id, conv.title)}
        style={{
          padding: '8px 10px',
          borderRadius: 'var(--radius-md, 8px)',
          background: isSelected ? '#EFF6FF' : 'transparent',
          border: isSelected ? '1px solid #BFDBFE' : '1px solid transparent',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          transition: 'all 0.14s ease'
        }}
        onMouseEnter={(e) => {
          if (!isSelected) e.currentTarget.style.background = 'var(--bg-subtle, #EEF4F0)';
        }}
        onMouseLeave={(e) => {
          if (!isSelected) e.currentTarget.style.background = 'transparent';
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
          <span style={{
            fontSize: '0.8rem',
            fontWeight: isSelected ? '700' : '600',
            color: isSelected ? '#1D4ED8' : 'var(--text-primary)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}>
            {conv.title || 'New Conversation'}
          </span>
          <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
            {formatTimestamp(conv.updated_at || conv.updatedAt || conv.created_at || conv.createdAt)}
          </span>
        </div>

        {/* Hover / Action Menu */}
        <div
          style={{ display: 'flex', alignItems: 'center', gap: '2px' }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setRenamingId(conv.id);
              setRenameInput(conv.title || 'New Conversation');
            }}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              padding: '3px',
              borderRadius: '4px'
            }}
            title="Rename"
          >
            <Edit3 size={13} />
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setDeletingId(conv.id);
            }}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              padding: '3px',
              borderRadius: '4px'
            }}
            title="Delete"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
    );
  }
};

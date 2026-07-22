import React, { useState, useEffect, useRef } from 'react';
import {
  getSupportConversations,
  createSupportConversation,
  getSupportConversationDetail,
  sendSupportMessage,
  updateSupportConversationStatus,
  uploadSupportAttachment,
  updateTypingStatus,
  getTypingStatus
} from '../../services/supportAPI';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export default function SupportChat({ role = "Organization Admin" }) {
  const isSuperAdmin = role === "Super Admin";
  
  const [conversations, setConversations] = useState([]);
  const [selectedConvId, setSelectedConvId] = useState(null);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [sending, setSending] = useState(false);
  
  // Filters & Search
  const [statusFilter, setStatusFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Reply Box
  const [replyText, setReplyText] = useState('');
  const [replyFile, setReplyFile] = useState(null);
  const [uploadingFile, setUploadingFile] = useState(false);
  
  // Typing state
  const [isOtherTyping, setIsOtherTyping] = useState(false);
  const typingTimeoutRef = useRef(null);
  
  // New Conversation Modal
  const [showModal, setShowModal] = useState(false);
  const [modalSubject, setModalSubject] = useState('');
  const [modalCategory, setModalCategory] = useState('Question');
  const [modalPriority, setModalPriority] = useState('Normal');
  const [modalMessage, setModalMessage] = useState('');
  const [modalFile, setModalFile] = useState(null);
  const [modalUploading, setModalUploading] = useState(false);
  
  // Media Lightbox
  const [previewImage, setPreviewImage] = useState(null);
  
  const messagesEndRef = useRef(null);
  
  // Auto-scroll messages to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // SuperAdmin orgs for creating tickets targeted at specific orgs
  const [superAdminOrgs, setSuperAdminOrgs] = useState([]);
  const [modalTargetOrg, setModalTargetOrg] = useState('');

  // Initial fetch
  useEffect(() => {
    fetchConversations();
    if (isSuperAdmin) {
      fetchSuperAdminOrgs();
    }
  }, [statusFilter, isSuperAdmin]);

  const fetchSuperAdminOrgs = async () => {
    try {
      const token = localStorage.getItem("superadmin_access_token");
      const res = await fetch(`${BACKEND_URL}/api/superadmin/organizations`, {
        headers: { "X-Super-Admin": "true", ...(token ? { "Authorization": `Bearer ${token}` } : {}) }
      });
      if (res.ok) {
        const data = await res.json();
        const orgList = data.organizations || data || [];
        setSuperAdminOrgs(orgList);
        if (orgList.length > 0 && !modalTargetOrg) {
          setModalTargetOrg(orgList[0].id);
        }
      }
    } catch (e) {
      console.error("Fetch super admin orgs error:", e);
    }
  };

  // Polling conversations & messages every 2 seconds for real-time responsiveness
  useEffect(() => {
    const interval = setInterval(() => {
      fetchConversations(true);
      if (selectedConvId) {
        fetchConversationDetail(selectedConvId, true);
        checkTyping(selectedConvId);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [selectedConvId, statusFilter, isSuperAdmin]);

  // When selected conversation changes
  useEffect(() => {
    if (selectedConvId) {
      fetchConversationDetail(selectedConvId);
    }
  }, [selectedConvId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOtherTyping]);

  const fetchConversations = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await getSupportConversations({ status: statusFilter, search: searchQuery }, isSuperAdmin);
      setConversations(data || []);
      if (!selectedConvId && data && data.length > 0 && !silent) {
        setSelectedConvId(data[0].id);
      }
    } catch (e) {
      console.error("Error fetching conversations:", e);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const fetchConversationDetail = async (convId, silent = false) => {
    if (!silent) setDetailLoading(true);
    try {
      const data = await getSupportConversationDetail(convId, isSuperAdmin);
      setActiveConv(data.conversation);
      setMessages(data.messages || []);
    } catch (e) {
      console.error("Error fetching conversation detail:", e);
    } finally {
      if (!silent) setDetailLoading(false);
    }
  };

  const checkTyping = async (convId) => {
    const res = await getTypingStatus(convId, isSuperAdmin);
    setIsOtherTyping(res?.is_typing || false);
  };

  const handleReplyChange = (e) => {
    setReplyText(e.target.value);
    
    if (selectedConvId) {
      updateTypingStatus(selectedConvId, true, isSuperAdmin);
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = setTimeout(() => {
        updateTypingStatus(selectedConvId, false, isSuperAdmin);
      }, 3000);
    }
  };

  const handleSendReply = async (e) => {
    e?.preventDefault();
    if (!selectedConvId || (!replyText.trim() && !replyFile) || sending) return;
    
    setSending(true);
    try {
      let attachmentUrl = null;
      if (replyFile) {
        setUploadingFile(true);
        const res = await uploadSupportAttachment(replyFile, isSuperAdmin);
        attachmentUrl = res.url;
        setUploadingFile(false);
      }

      await sendSupportMessage(selectedConvId, {
        message: replyText.trim(),
        attachment: attachmentUrl
      }, isSuperAdmin);

      setReplyText('');
      setReplyFile(null);
      updateTypingStatus(selectedConvId, false, isSuperAdmin);
      fetchConversationDetail(selectedConvId, true);
      fetchConversations(true);
    } catch (err) {
      alert("Failed to send message: " + err.message);
    } finally {
      setSending(false);
      setUploadingFile(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    if (!selectedConvId) return;
    try {
      await updateSupportConversationStatus(selectedConvId, { status: newStatus }, isSuperAdmin);
      fetchConversationDetail(selectedConvId, true);
      fetchConversations(true);
    } catch (err) {
      alert("Failed to update status: " + err.message);
    }
  };

  const handlePriorityChange = async (newPriority) => {
    if (!selectedConvId) return;
    try {
      await updateSupportConversationStatus(selectedConvId, { priority: newPriority }, isSuperAdmin);
      fetchConversationDetail(selectedConvId, true);
      fetchConversations(true);
    } catch (err) {
      alert("Failed to update priority: " + err.message);
    }
  };

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    if (!modalMessage.trim() && !modalFile) return;

    setModalUploading(true);
    try {
      let attachmentUrl = null;
      if (modalFile) {
        const res = await uploadSupportAttachment(modalFile, isSuperAdmin);
        attachmentUrl = res.url;
      }

      const res = await createSupportConversation({
        subject: modalSubject.trim() || `${modalCategory} - Support Request`,
        category: modalCategory,
        priority: modalPriority,
        message: modalMessage.trim(),
        attachment: attachmentUrl,
        ...(isSuperAdmin && modalTargetOrg ? { organization_id: modalTargetOrg } : {})
      }, isSuperAdmin);

      setShowModal(false);
      setModalSubject('');
      setModalMessage('');
      setModalFile(null);
      
      await fetchConversations();
      if (res.conversation?.id) {
        setSelectedConvId(res.conversation.id);
      }
    } catch (err) {
      alert("Failed to create ticket: " + err.message);
    } finally {
      setModalUploading(false);
    }
  };

  const getPriorityBadgeClass = (p) => {
    switch (p) {
      case 'Urgent': return 'badge-urgent';
      case 'High': return 'badge-high';
      case 'Normal': return 'badge-normal';
      default: return 'badge-low';
    }
  };

  const getStatusBadgeClass = (s) => {
    switch (s) {
      case 'Open': return 'badge-open';
      case 'In Progress': return 'badge-inprogress';
      case 'Resolved': return 'badge-resolved';
      case 'Closed': return 'badge-closed';
      default: return 'badge-open';
    }
  };

  const renderAttachment = (url) => {
    if (!url) return null;
    const fullUrl = url.startsWith('/') ? `${BACKEND_URL}${url}` : url;
    const isImage = /\.(jpeg|jpg|gif|png|webp|svg)/i.test(url);

    if (isImage) {
      return (
        <div style={{ marginTop: '8px' }}>
          <img
            src={fullUrl}
            alt="Attachment"
            onClick={() => setPreviewImage(fullUrl)}
            style={{
              maxWidth: '240px',
              maxHeight: '180px',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.15)',
              cursor: 'pointer',
              objectFit: 'cover'
            }}
          />
        </div>
      );
    }

    return (
      <div style={{ marginTop: '8px' }}>
        <a
          href={fullUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(255,255,255,0.06)',
            padding: '6px 12px',
            borderRadius: '6px',
            color: 'var(--cyan, #00c4a7)',
            fontSize: '12px',
            textDecoration: 'none',
            border: '1px solid rgba(255,255,255,0.1)'
          }}
        >
          📎 Attachment File ↗
        </a>
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 100px)', gap: '16px' }}>
      
      {/* SCOPE INLINE CSS FOR CHAT COMPONENT */}
      <style>{`
        .chat-container {
          display: flex;
          flex: 1;
          background: rgba(10, 15, 29, 0.95);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
          backdrop-filter: blur(10px);
        }

        .chat-sidebar {
          width: 320px;
          border-right: 1px solid rgba(255, 255, 255, 0.08);
          display: flex;
          flex-direction: column;
          background: rgba(6, 10, 20, 0.6);
        }

        .chat-main {
          flex: 1;
          display: flex;
          flex-direction: column;
          background: rgba(8, 12, 24, 0.4);
        }

        .conv-card {
          padding: 12px 14px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.04);
          cursor: pointer;
          transition: all 0.15s ease;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .conv-card:hover {
          background: rgba(255, 255, 255, 0.03);
        }

        .conv-card.active {
          background: linear-gradient(135deg, rgba(124, 79, 224, 0.18), rgba(0, 196, 167, 0.12));
          border-left: 3px solid #00c4a7;
        }

        .badge-open { background: rgba(0, 196, 167, 0.15); color: #00c4a7; border: 1px solid rgba(0, 196, 167, 0.3); }
        .badge-inprogress { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-resolved { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-closed { background: rgba(100, 116, 139, 0.2); color: #94a3b8; border: 1px solid rgba(100, 116, 139, 0.3); }

        .badge-urgent { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        .badge-high { background: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.4); }
        .badge-normal { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
        .badge-low { background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }

        .chat-bubble {
          max-width: 75%;
          padding: 10px 14px;
          border-radius: 12px;
          font-size: 13px;
          line-height: 1.45;
          position: relative;
          word-break: break-word;
        }

        .bubble-me {
          align-self: flex-end;
          background: linear-gradient(135deg, #7c4fe0, #5c28c6);
          color: #fff;
          border-bottom-right-radius: 2px;
          box-shadow: 0 4px 12px rgba(124, 79, 224, 0.25);
        }

        .bubble-other {
          align-self: flex-start;
          background: rgba(22, 30, 48, 0.9);
          border: 1px solid rgba(255, 255, 255, 0.08);
          color: #e2e8f0;
          border-bottom-left-radius: 2px;
        }
      `}</style>

      {/* HEADER TITLE BAR */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 900, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            💬 Internal Support Chat System
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text2, #94a3b8)', marginTop: '2px', margin: 0 }}>
            {isSuperAdmin
              ? 'Real-time internal support queue for Organization Admins & Enterprise Clients'
              : 'Direct live support channel with PrepFly Super Admins & Engineering Team'}
          </p>
        </div>

        {!isSuperAdmin && (
          <button
            className="btn btn-primary"
            onClick={() => setShowModal(true)}
            style={{
              background: 'linear-gradient(135deg, #00c4a7, #7c4fe0)',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 16px',
              fontWeight: 800,
              fontSize: '13px',
              color: '#fff',
              cursor: 'pointer'
            }}
          >
            ➕ New Support Ticket
          </button>
        )}
      </div>

      {/* MAIN CONTAINER SPLIT VIEW */}
      <div className="chat-container">
        
        {/* LEFT CONVERSATIONS LIST SIDEBAR */}
        <div className="chat-sidebar">
          
          {/* SEARCH & FILTERS */}
          <div style={{ padding: '12px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
                padding: '7px 12px',
                fontSize: '12px',
                color: '#fff',
                outline: 'none'
              }}
            />

            {/* STATUS FILTER TABS */}
            <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', paddingBottom: '2px' }}>
              {['All', 'Open', 'In Progress', 'Resolved', 'Closed'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setStatusFilter(tab)}
                  style={{
                    background: statusFilter === tab ? 'rgba(0,196,167,0.2)' : 'transparent',
                    border: statusFilter === tab ? '1px solid rgba(0,196,167,0.4)' : '1px solid transparent',
                    color: statusFilter === tab ? '#00c4a7' : '#94a3b8',
                    padding: '3px 8px',
                    borderRadius: '6px',
                    fontSize: '11px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* CONVERSATION LIST */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {loading ? (
              <div style={{ color: '#00c4a7', padding: '24px', textAlign: 'center', fontSize: '12px' }}>
                ⚡ Loading conversations...
              </div>
            ) : conversations.length === 0 ? (
              <div style={{ color: '#94a3b8', padding: '24px', textAlign: 'center', fontSize: '12px' }}>
                No support conversations found.
              </div>
            ) : (
              conversations.map(conv => {
                const isSelected = conv.id === selectedConvId;
                return (
                  <div
                    key={conv.id}
                    className={`conv-card ${isSelected ? 'active' : ''}`}
                    onClick={() => setSelectedConvId(conv.id)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '10px', textTransform: 'uppercase', fontWeight: 800, color: 'var(--text2, #94a3b8)' }}>
                        {isSuperAdmin ? conv.organization_name : conv.category}
                      </span>
                      <span className={`pill ${getStatusBadgeClass(conv.status)}`} style={{ fontSize: '9px', padding: '1px 6px', borderRadius: '4px' }}>
                        {conv.status}
                      </span>
                    </div>

                    <div style={{ fontWeight: 800, fontSize: '13px', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {conv.subject}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2px' }}>
                      <div style={{ fontSize: '11px', color: '#94a3b8', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {conv.last_message ? (conv.last_message.message || '📷 Attachment') : 'No messages'}
                      </div>
                      
                      {conv.unread_count > 0 && (
                        <span style={{
                          background: '#ec4899',
                          color: '#fff',
                          fontSize: '10px',
                          fontWeight: 900,
                          padding: '2px 6px',
                          borderRadius: '10px'
                        }}>
                          {conv.unread_count}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px', fontSize: '10px', color: '#64748b' }}>
                      <span className={`pill ${getPriorityBadgeClass(conv.priority)}`} style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '4px' }}>
                        ● {conv.priority}
                      </span>
                      <span>{conv.updated_at ? conv.updated_at.split(' ')[1] || conv.updated_at : ''}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT CHAT THREAD PANEL */}
        <div className="chat-main">
          {selectedConvId && activeConv ? (
            <>
              {/* CHAT THREAD HEADER */}
              <div style={{
                padding: '12px 18px',
                borderBottom: '1px solid rgba(255,255,255,0.06)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'rgba(10,15,28,0.4)'
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#fff', margin: 0 }}>
                      {activeConv.subject}
                    </h3>
                    <span className={`pill ${getStatusBadgeClass(activeConv.status)}`} style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '6px' }}>
                      {activeConv.status}
                    </span>
                  </div>

                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px', display: 'flex', gap: '12px' }}>
                    <span>🏛 {activeConv.organization_name}</span>
                    <span>🏷 Category: {activeConv.category}</span>
                    <span>⚡ Priority: {activeConv.priority}</span>
                  </div>
                </div>

                {/* SUPER ADMIN OR ORG ADMIN ACTIONS */}
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {isSuperAdmin && (
                    <select
                      value={activeConv.priority || 'Normal'}
                      onChange={(e) => handlePriorityChange(e.target.value)}
                      style={{
                        background: 'rgba(255,255,255,0.06)',
                        border: '1px solid rgba(255,255,255,0.12)',
                        borderRadius: '6px',
                        color: '#fff',
                        fontSize: '11px',
                        padding: '4px 8px',
                        outline: 'none'
                      }}
                    >
                      <option value="Low">Priority: Low</option>
                      <option value="Normal">Priority: Normal</option>
                      <option value="High">Priority: High</option>
                      <option value="Urgent">Priority: Urgent</option>
                    </select>
                  )}

                  {activeConv.status !== 'Resolved' && (
                    <button
                      onClick={() => handleStatusChange('Resolved')}
                      style={{
                        background: 'rgba(16,185,129,0.15)',
                        border: '1px solid rgba(16,185,129,0.3)',
                        color: '#10b981',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '5px 10px',
                        cursor: 'pointer'
                      }}
                    >
                      ✓ Mark Resolved
                    </button>
                  )}

                  {activeConv.status !== 'Closed' ? (
                    <button
                      onClick={() => handleStatusChange('Closed')}
                      style={{
                        background: 'rgba(239,68,68,0.12)',
                        border: '1px solid rgba(239,68,68,0.3)',
                        color: '#f87171',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '5px 10px',
                        cursor: 'pointer'
                      }}
                    >
                      🔒 Close Ticket
                    </button>
                  ) : (
                    <button
                      onClick={() => handleStatusChange('Open')}
                      style={{
                        background: 'rgba(0,196,167,0.15)',
                        border: '1px solid rgba(0,196,167,0.3)',
                        color: '#00c4a7',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '5px 10px',
                        cursor: 'pointer'
                      }}
                    >
                      🔄 Reopen Ticket
                    </button>
                  )}
                </div>
              </div>

              {/* MESSAGES FEED */}
              <div style={{ flex: 1, padding: '16px 20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {detailLoading ? (
                  <div style={{ color: '#00c4a7', textAlign: 'center', margin: 'auto', fontSize: '12px' }}>
                    ⚡ Loading messages...
                  </div>
                ) : (
                  messages.map(msg => {
                    const isMe = msg.sender_role === role;
                    return (
                      <div
                        key={msg.id}
                        className={`chat-bubble ${isMe ? 'bubble-me' : 'bubble-other'}`}
                      >
                        <div style={{ fontSize: '10px', opacity: 0.8, marginBottom: '4px', display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                          <span style={{ fontWeight: 800 }}>
                            {msg.sender_role === "Super Admin" ? "👑 Super Admin" : "🏛 Org Admin"}
                          </span>
                          <span>{msg.created_at}</span>
                        </div>

                        <div>{msg.message}</div>

                        {renderAttachment(msg.attachment)}

                        {isMe && (
                          <div style={{ textAlign: 'right', fontSize: '9px', opacity: 0.7, marginTop: '4px' }}>
                            {msg.is_read ? '✓✓ Seen' : '✓ Sent'}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}

                {/* TYPING INDICATOR */}
                {isOtherTyping && (
                  <div className="chat-bubble bubble-other" style={{ fontSize: '11px', fontStyle: 'italic', color: '#00c4a7' }}>
                    ✍️ {isSuperAdmin ? 'Organization Admin' : 'Super Admin'} is typing...
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* REPLY BOX FOOTER */}
              <form onSubmit={handleSendReply} style={{ padding: '12px 18px', borderTop: '1px solid rgba(255,255,255,0.06)', background: 'rgba(6,10,20,0.6)' }}>
                {replyFile && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', background: 'rgba(255,255,255,0.05)', padding: '6px 10px', borderRadius: '6px', width: 'fit-content' }}>
                    <span style={{ fontSize: '11px', color: '#00c4a7' }}>📎 {replyFile.name}</span>
                    <button type="button" onClick={() => setReplyFile(null)} style={{ background: 'none', border: 'none', color: '#ff5472', cursor: 'pointer', fontSize: '12px' }}>✕</button>
                  </div>
                )}

                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <label
                    title="Upload screenshot or document"
                    style={{
                      background: 'rgba(255,255,255,0.06)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      cursor: 'pointer',
                      fontSize: '16px',
                      color: 'var(--text2, #94a3b8)',
                      userSelect: 'none'
                    }}
                  >
                    📷
                    <input
                      type="file"
                      style={{ display: 'none' }}
                      onChange={(e) => e.target.files?.[0] && setReplyFile(e.target.files[0])}
                    />
                  </label>

                  <input
                    type="text"
                    placeholder={activeConv.status === 'Closed' ? "Ticket closed. Sending a reply will reopen it..." : "Type your support message..."}
                    value={replyText}
                    onChange={handleReplyChange}
                    style={{
                      flex: 1,
                      background: 'rgba(255,255,255,0.04)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      padding: '10px 14px',
                      fontSize: '13px',
                      color: '#fff',
                      outline: 'none'
                    }}
                  />

                  <button
                    type="submit"
                    disabled={sending || uploadingFile || (!replyText.trim() && !replyFile)}
                    style={{
                      background: 'linear-gradient(135deg, #00c4a7, #7c4fe0)',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '10px 18px',
                      fontWeight: 800,
                      fontSize: '13px',
                      color: '#fff',
                      cursor: sending || uploadingFile || (!replyText.trim() && !replyFile) ? 'not-allowed' : 'pointer',
                      opacity: sending || uploadingFile || (!replyText.trim() && !replyFile) ? 0.5 : 1
                    }}
                  >
                    {sending ? 'Sending...' : 'Send 🚀'}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <div style={{ margin: 'auto', color: '#94a3b8', textAlign: 'center' }}>
              <div style={{ fontSize: '32px', marginBottom: '8px' }}>💬</div>
              <div style={{ fontWeight: 800, fontSize: '15px' }}>Select a conversation</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Choose a support thread from the left or create a new ticket.</div>
            </div>
          )}
        </div>
      </div>

      {/* NEW SUPPORT TICKET MODAL */}
      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: '#0a0f1d',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: '16px',
            width: '460px',
            padding: '24px',
            boxShadow: '0 20px 50px rgba(0,0,0,0.8)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 900, color: '#fff', margin: 0 }}>
                ➕ Create Support Conversation
              </h3>
              <button
                onClick={() => setShowModal(false)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '16px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTicket} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {isSuperAdmin && (
                <div>
                  <label style={{ fontSize: '11px', fontWeight: 800, color: 'var(--cyan)', display: 'block', marginBottom: '4px' }}>Target Organization *</label>
                  <select
                    value={modalTargetOrg}
                    onChange={(e) => setModalTargetOrg(e.target.value)}
                    style={{ width: '100%', background: '#141d30', border: '1px solid rgba(0,196,167,0.3)', borderRadius: '8px', padding: '8px 12px', fontSize: '12px', color: '#fff', outline: 'none' }}
                  >
                    {superAdminOrgs.map(o => (
                      <option key={o.id} value={o.id}>
                        🏛 {o.name || o.organization_name || o.id}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label style={{ fontSize: '11px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Subject Title</label>
                <input
                  type="text"
                  placeholder="e.g. WebRTC Video Session Audio Lag"
                  value={modalSubject}
                  onChange={(e) => setModalSubject(e.target.value)}
                  style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px 12px', fontSize: '12px', color: '#fff', outline: 'none' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '11px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Category</label>
                  <select
                    value={modalCategory}
                    onChange={(e) => setModalCategory(e.target.value)}
                    style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px 12px', fontSize: '12px', color: '#fff', outline: 'none' }}
                  >
                    <option value="Question">Ask Question</option>
                    <option value="Report Bug">Report Bug</option>
                    <option value="Feature Request">Request Feature</option>
                    <option value="General">General Support</option>
                  </select>
                </div>

                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '11px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Priority Level</label>
                  <select
                    value={modalPriority}
                    onChange={(e) => setModalPriority(e.target.value)}
                    style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px 12px', fontSize: '12px', color: '#fff', outline: 'none' }}
                  >
                    <option value="Low">Low</option>
                    <option value="Normal">Normal</option>
                    <option value="High">High</option>
                    <option value="Urgent">Urgent 🔥</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '11px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Description / Initial Message</label>
                <textarea
                  rows={4}
                  placeholder="Describe your issue or request in detail..."
                  value={modalMessage}
                  onChange={(e) => setModalMessage(e.target.value)}
                  style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px 12px', fontSize: '12px', color: '#fff', outline: 'none', resize: 'vertical' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', fontWeight: 800, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Attach Screenshot / File (Optional)</label>
                <input
                  type="file"
                  onChange={(e) => e.target.files?.[0] && setModalFile(e.target.files[0])}
                  style={{ fontSize: '12px', color: '#94a3b8' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8', borderRadius: '8px', padding: '8px 16px', fontSize: '12px', cursor: 'pointer' }}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={modalUploading || (!modalMessage.trim() && !modalFile)}
                  style={{ background: 'linear-gradient(135deg, #00c4a7, #7c4fe0)', border: 'none', color: '#fff', borderRadius: '8px', padding: '8px 20px', fontWeight: 800, fontSize: '12px', cursor: 'pointer' }}
                >
                  {modalUploading ? 'Creating...' : 'Submit Support Ticket'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* IMAGE PREVIEW LIGHTBOX */}
      {previewImage && (
        <div
          onClick={() => setPreviewImage(null)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2000,
            cursor: 'zoom-out'
          }}
        >
          <img src={previewImage} alt="Fullscreen Preview" style={{ maxWidth: '90%', maxHeight: '90%', borderRadius: '12px', boxShadow: '0 10px 40px rgba(0,0,0,0.8)' }} />
        </div>
      )}

    </div>
  );
}

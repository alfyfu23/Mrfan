"use client";

import { useMemo, useState, useEffect, useCallback } from "react";
import { useUserContext } from "@/context/UserContext";
import { BACKEND_URL } from "@/constant/strings";
import { Message } from "@/types/Message";
import UserTooltip from "./UserTooltip";
import Avatar from "./Avatar";
import { getThemedColor } from '@/utils/themeDetector';

interface FriendsListProps {
    conversationId: number | null;
    onSelect: (id: number) => void;
    filterText?: string;
}

// 获取消息预览的辅助函数
function getMessagePreview(message: Message): string {
    if (!message) return '暂无消息';
    if (!message.text) return '暂无消息';
    const text = String(message.text);
    return text.length > 30 ? text.substring(0, 30) + '...' : text;
}

export default function FriendsList({ conversationId, onSelect, filterText = "" }: FriendsListProps) {
    const { conversations, isLoading, pinConversation, unpinConversation, toggleMuteConversation, selfId, id_to_username, isUserOnline } = useUserContext();

    const [hoveredId, setHoveredId] = useState<number | null>(null);
    const [contextMenu, setContextMenu] = useState<{ x: number; y: number; convId: number } | null>(null);

    const getConversationName = useCallback((conv: typeof conversations[number]) => {
        if (conv.isGroup) return conv.name || '未命名会话';
        const otherMember = conv.member?.find(m => m.id !== selfId);
        const profile = otherMember ? id_to_username[otherMember.id] : undefined;
        const fallback = otherMember?.nickname || otherMember?.display_username || conv.name || '未命名会话';
        return profile?.name || fallback;
    }, [id_to_username, selfId]);
 
    // 点击外部区域关闭右键菜单
    useEffect(() => {
        const handleClickOutside = () => setContextMenu(null);
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, []);

    const visibleConversations = useMemo(() => {
        const normalized = filterText.trim().toLowerCase();
        let filteredConversations = conversations;
        
        if (normalized) {
            filteredConversations = conversations.filter(conv => getConversationName(conv).toLowerCase().includes(normalized));
        }
        
        // 排序：置顶的会话在前，并按pinOrder排序；非置顶的会话在后
        return filteredConversations.sort((a, b) => {
            // 如果a是置顶的，b不是，a在前
            if (a.isPinned && !b.isPinned) return -1;
            // 如果b是置顶的，a不是，b在前
            if (!a.isPinned && b.isPinned) return 1;
            // 如果都是置顶的，按pinOrder排序（数字越小越靠前）
            if (a.isPinned && b.isPinned) {
                return (a.pinOrder || 0) - (b.pinOrder || 0);
            }
            // 如果都不是置顶的，按最后消息时间排序（最新的在前）
            const aLastTime = a.messages && a.messages.length > 0
                ? a.messages[a.messages.length - 1].timestamp.getTime()
                : 0;
            const bLastTime = b.messages && b.messages.length > 0
                ? b.messages[b.messages.length - 1].timestamp.getTime()
                : 0;
            return bLastTime - aLastTime;
        });
    }, [conversations, filterText, getConversationName]);

    return (
        <div className="friends-list-container">
            <div className="friends-list-header">
                聊天列表
            </div>
            <div className="friends-list-content">
                {isLoading && (
                    <div className="loading-message">加载会话中…</div>
                )}
                {!isLoading && visibleConversations.length === 0 && (
                    <div className="empty-message">暂无会话</div>
                )}
                {!isLoading && visibleConversations.map(conv => {
                    const isPrivate = conv.isGroup === false;
                    const otherMember = isPrivate ? conv.member.find(m => m.id !== selfId) : undefined;
                    const otherProfile = otherMember ? id_to_username[otherMember.id] : undefined;
                    const tooltipUser = otherMember ? {
                        id: otherMember.id,
                        nickname: otherProfile?.name || otherMember.nickname || conv.name,
                        username: otherProfile?.name || otherMember.display_username || otherMember.nickname || conv.name,
                        avatar: otherProfile?.avatar || otherMember.avatar || conv.avatar || `https://${BACKEND_URL}/asset/default.png`,
                        is_online: isUserOnline(otherMember.id),
                        is_active: otherMember.is_active,
                        info: otherProfile?.info,
                    } : undefined;
                    const showDeactivated = otherMember?.is_active === false;
                    const displayNameBase = getConversationName(conv);
                    const displayName = `${displayNameBase}${showDeactivated ? ' (已注销)' : ''}`;
                    const avatarElement = (
                        <div className="conversation-avatar">
                            <Avatar
                                src={conv.avatar}
                                size={48}
                                alt={displayNameBase || 'avatar'}
                                className="avatar-image"
                                fallbackText={displayNameBase?.charAt(0)}
                            />
                        </div>
                    );
                    return (
                    <div
                        key={conv.id}
                        onClick={() => onSelect(conv.id)}
                        onMouseEnter={() => setHoveredId(conv.id)}
                        onMouseLeave={() => setHoveredId(null)}
                        onContextMenu={(e) => {
                            e.preventDefault();
                            // 获取当前会话项的位置信息
                            const rect = e.currentTarget.getBoundingClientRect();
                            // 计算会话项的中心位置
                            const centerX = rect.left + rect.width / 2;
                            const centerY = rect.top + rect.height / 2;
                            setContextMenu({ x: centerX, y: centerY, convId: conv.id });
                        }}
                        className={`conversation-item ${conversationId === conv.id ? 'active' : ''} ${hoveredId === conv.id ? 'hovered' : ''}`}
                    >
                        {isPrivate && tooltipUser ? (
                            <UserTooltip user={tooltipUser}>
                                {avatarElement}
                            </UserTooltip>
                        ) : avatarElement}
                        <div className="conversation-info">
                            <div className="conversation-name">{displayName}</div>
                            <div className="conversation-preview">
                                {conv.messages && conv.messages.length > 0 
                                    ? getMessagePreview(conv.messages[conv.messages.length - 1])
                                    : '暂无消息'
                                }
                            </div>
                        </div>
                        <div className="conversation-meta">
                            <div className="conversation-time">
                                {conv.messages && conv.messages.length > 0
                                    ? new Date(conv.messages[conv.messages.length - 1].timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                                    : ''
                                }
                            </div>
                            <div className="conversation-status">
                                {/* 显示置顶图标 */}
                                {conv.isPinned && (
                                    <div className="pin-indicator" title="已置顶">📌</div>
                                )}
                                {/* 显示免打扰图标 */}
                                {conv.isMuted && (
                                    <div className="mute-indicator" title="免打扰">🔕</div>
                                )}
                                {/* 显示未读计数（群聊和私聊都显示，且未开启免打扰） */}
                                {!!conv.unread_count && conv.unread_count > 0 && !conv.isMuted && (
                                    <div
                                        className="unread-badge"
                                        style={{
                                            color: getThemedColor('#ffffff', '#ffffff'),
                                            background: getThemedColor(
                                                'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)',
                                                'linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%)'
                                            )
                                        }}
                                    >
                                        {conv.unread_count > 99 ? '99+' : conv.unread_count}
                                    </div>
                                )}
                                {/* 对于私聊且没有未读消息的情况，显示最后一条消息的已读/未读状态 */}
                                {conv.member && conv.member.length <= 2 && (!conv.unread_count || conv.unread_count === 0) && conv.messages && conv.messages.length > 0 && (
                                    <div className="read-status">
                                        {(() => {
                                            const lastMessage = conv.messages[conv.messages.length - 1];
                                            // 如果是自己发送的消息，检查对方是否已读
                                            if (lastMessage.sender === selfId) {
                                                // 检查read_by数组中是否包含对方ID
                                                const otherMemberId = conv.member.find(m => m.id !== selfId)?.id;
                                                const isReadByOther = otherMemberId && lastMessage.read_by?.includes(otherMemberId);
                                                return isReadByOther ? (
                                                    <div className="read-indicator read" title="已读"></div>
                                                ) : (
                                                    <div className="read-indicator unread" title="未读"></div>
                                                );
                                            } else {
                                                // 如果是对方发送的消息，检查is_read字段
                                                return lastMessage.is_read ? (
                                                    <div className="read-indicator read" title="已读"></div>
                                                ) : (
                                                    <div className="read-indicator unread" title="未读"></div>
                                                );
                                            }
                                        })()}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                    );
                })}
            </div>
            
            {/* 右键菜单 */}
            {contextMenu && (
                <div
                    className="context-menu"
                    style={{
                        position: 'fixed',
                        left: `${contextMenu.x}px`,
                        top: `${contextMenu.y}px`,
                        transform: 'translate(-50%, -50%)', // 使菜单中心对齐到计算的中心点
                        zIndex: 2147483647 // 使用最大z-index确保菜单不会被其他组件遮住
                    }}
                >
                            <div
                                className="context-menu-item"
                                onClick={() => {
                                    const conv = conversations.find(c => c.id === contextMenu.convId);
                                    if (conv) {
                                        if (conv.isPinned) {
                                            unpinConversation(contextMenu.convId);
                                        } else {
                                            pinConversation(contextMenu.convId);
                                        }
                                    }
                                    setContextMenu(null);
                                }}
                            >
                                {conversations.find(c => c.id === contextMenu.convId)?.isPinned ? '取消置顶' : '置顶'}
                            </div>
                            <div
                                className="context-menu-item"
                                onClick={() => {
                                    const conv = conversations.find(c => c.id === contextMenu.convId);
                                    if (conv) {
                                        toggleMuteConversation(contextMenu.convId, !conv.isMuted);
                                    }
                                    setContextMenu(null);
                                }}
                            >
                                {conversations.find(c => c.id === contextMenu.convId)?.isMuted ? '开启提醒' : '消息免打扰'}
                            </div>
                </div>
            )}
            
            <style jsx>{`
                .friends-list-container {
                    display: flex;
                    flex-direction: column;
                    height: 100%;
                    overflow: hidden;
                }

                .friends-list-header {
                    padding: 16px 20px;
                    font-weight: 600;
                    font-size: 18px;
                    color: #333;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
                    background: rgba(255, 255, 255, 0.8);
                }

                .friends-list-content {
                    flex: 1;
                    overflow-y: auto;
                    padding: 8px 0;
                }

                .loading-message, .empty-message {
                    padding: 20px;
                    text-align: center;
                    color: #888;
                    font-size: 14px;
                }

                .conversation-item {
                    display: flex;
                    align-items: center;
                    padding: 12px 20px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.03);
                    position: relative;
                }

                .conversation-item:hover {
                    background: rgba(102, 126, 234, 0.08);
                }

                .conversation-item.active {
                    background: linear-gradient(90deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.1) 100%);
                    border-left: 3px solid #667eea;
                }

                .conversation-avatar {
                    width: 48px;
                    height: 48px;
                    margin-right: 12px;
                    flex-shrink: 0;
                    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
                }

                .conversation-info {
                    flex: 1;
                    min-width: 0;
                }

                .conversation-name {
                    font-weight: 600;
                    font-size: 16px;
                    color: #333;
                    margin-bottom: 4px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                .conversation-preview {
                    font-size: 13px;
                    color: #666;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                .conversation-meta {
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    gap: 4px;
                }

                .conversation-time {
                    font-size: 11px;
                    color: #999;
                }

                .conversation-status {
                    display: flex;
                    align-items: center;
                    justify-content: flex-end;
                    gap: 4px;
                }

                .unread-badge {
                    border-radius: 10px;
                    padding: 2px 8px;
                    font-size: 11px;
                    font-weight: 600;
                    min-width: 18px;
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(255, 77, 79, 0.3);
                    z-index: 1;
                    position: relative;
                    transition: all 0.2s ease;
                }

                .read-status {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .read-indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 50%;
                    transition: all 0.2s ease;
                }

                .read-indicator.read {
                    background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
                    box-shadow: 0 1px 3px rgba(82, 196, 26, 0.3);
                }

                .read-indicator.unread {
                    border: 2px solid #d9d9d9;
                    background: transparent;
                }

                .conversation-item.active .conversation-name {
                    color: #667eea;
                }

                .conversation-item.active .conversation-preview {
                    color: #555;
                }
                
                /* 置顶指示器样式 */
                .pin-indicator, .mute-indicator {
                    font-size: 14px;
                    margin-left: 4px;
                }
                
                .pin-indicator {
                    animation: pulse 2s infinite;
                }
                
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.1); }
                    100% { transform: scale(1); }
                }
                
                /* 右键菜单样式 */
                .context-menu {
                    position: fixed;
                    background: white;
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    padding: 8px 0;
                    min-width: 120px;
                    z-index: 2147483647; /* 使用最大z-index确保菜单不会被其他组件遮住 */
                    pointer-events: auto; /* 确保菜单可以接收鼠标事件 */
                }
                
                .context-menu-item {
                    padding: 8px 16px;
                    cursor: pointer;
                    border-radius: 4px;
                    transition: background 0.2s ease;
                    font-size: 14px;
                }
                
                .context-menu-item:hover {
                    background: rgba(102, 126, 234, 0.1);
                }
            `}</style>
        </div>
    );
}
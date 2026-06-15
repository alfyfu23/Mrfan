"use client";

import { useEffect, useMemo, useState } from "react";
import type { StaticImageData } from "next/image";
import { useUserContext } from "@/context/UserContext";
import FriendsList from "./FriendsList";
import SearchBar, { SearchBarActionKey } from "./SearchBar";
import ChatBox from "./ChatRoom";
import SocialPanel from "./SocialPanel";
import SettingsPanel from "./SettingsPanel";
import UserTooltip from "./UserTooltip";
import chatIcon from "../../asset/chat.png";
import friendIcon from "../../asset/friend.jpg";
import settingIcon from "../../asset/setting.jpg";

type TabKey = "chat" | "friends" | "settings";
type AssetSource = string | StaticImageData;

const resolveAssetSrc = (asset: AssetSource) => (typeof asset === "string" ? asset : asset.src);

export default function MainPage() {
    const { selfAvatar, username, selfId } = useUserContext();

    const [conversationId, setConversationId] = useState<number | null>(null);
    const [tab, setTab] = useState<TabKey>('chat');
    const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
    const [chatSearch, setChatSearch] = useState("");
    const [sidebarWidth, setSidebarWidth] = useState(320); // 侧边栏宽度状态
    const [isResizing, setIsResizing] = useState(false); // 是否正在调整大小
    
    useEffect(() => { setAvatarUrl(selfAvatar ?? null); }, [selfAvatar]);
    
    // 处理调整大小的逻辑
    useEffect(() => {
        if (!isResizing) return;
        
        const handleMouseMove = (e: MouseEvent) => {
            const newWidth = e.clientX - 64; // 减去左侧导航栏的宽度
            if (newWidth >= 250 && newWidth <= 500) { // 设置最小和最大宽度限制
                setSidebarWidth(newWidth);
            }
        };
        
        const handleMouseUp = () => {
            setIsResizing(false);
        };
        
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isResizing]);

    const navItems = useMemo<Array<{ key: TabKey; icon: AssetSource; alt: string }>>(() => ([
        { key: 'chat', icon: chatIcon, alt: '聊天' },
        { key: 'friends', icon: friendIcon, alt: '好友' },
    ]), []);

    // 不再需要resolvedAvatar，因为Avatar组件会处理默认头像

    const handleQuickAction = (action: SearchBarActionKey) => {
        if (action === 'add-friend') {
            setTab('friends');
        } else if (action === 'start-group') {
            setTab('chat');
        }
    };

    const handleChatSearch = () => {
        setChatSearch(prev => prev.trim());
    };

    const handleGroupCreated = (convId: number) => {
        setConversationId(convId);
        setTab('chat');
        setChatSearch('');
    };

    return (
        <div className="main-container">
            {/* 最左侧图标竖栏：仅图标、无文字 */}
            <div className="sidebar-nav">
                {/* 用户头像在最左列顶部 */}
                <UserTooltip user={{
                    id: selfId || 0,
                    nickname: username || '',
                    username: username || '',
                    avatar: avatarUrl || '',
                    is_online: true
                }}>
                    <button title="用户信息" className="user-avatar-button">
                        {avatarUrl ? (
                            <img src={avatarUrl} alt="me" className="user-avatar" />
                        ) : (
                            <div className="user-avatar-placeholder">
                                {(username || 'U').charAt(0).toUpperCase()}
                            </div>
                        )}
                    </button>
                </UserTooltip>
                {navItems.map(item => (
                    <button key={item.key}
                        onClick={() => setTab(item.key)}
                        title={item.alt}
                        className={`nav-button ${tab === item.key ? 'active' : ''}`}
                    >
                        <img src={resolveAssetSrc(item.icon)} alt={item.alt} className="nav-icon" />
                    </button>
                ))}
                <button 
                    onClick={() => setTab('settings')} 
                    title="设置" 
                    className={`nav-button ${tab === 'settings' ? 'active' : ''}`}
                >
                    <img src={resolveAssetSrc(settingIcon)} alt="设置" className="nav-icon" />
                </button>
            </div>

            {/* 左侧面板（与图标栏平行） */}
            <div className="sidebar-panel">
                {/* 调整大小的手柄 */}
                <div
                    className="resize-handle"
                    onMouseDown={() => setIsResizing(true)}
                />
                {/* 左栏主体 */}
                {tab === 'chat' && (
                    <>
                        <div className="search-container">
                            <SearchBar
                                value={chatSearch}
                                placeholder="搜索好友或群聊..."
                                onChange={setChatSearch}
                                onSearch={handleChatSearch}
                                onActionSelect={handleQuickAction}
                                onGroupCreated={handleGroupCreated}
                                actions={[{ key: "add-friend", label: "添加好友" }, { key: "start-group", label: "发起群聊" }]}
                            />
                        </div>
                        <FriendsList conversationId={conversationId} onSelect={id => setConversationId(id)} filterText={chatSearch} />
                    </>
                )}
                {tab === 'friends' && (
                    <div className="panel-content">
                        <SocialPanel onGroupCreated={handleGroupCreated} />
                    </div>
                )}
                {tab === 'settings' && (
                    <div className="panel-content">
                        <SettingsPanel />
                    </div>
                )}
            </div>
            {/* 右侧区域 */}
            {tab === 'chat' ? <ChatBox conversationId={conversationId} /> : (
                <div className="empty-state">
                    {tab === 'friends' ? '在左侧管理好友；选择需要的操作。' : '在左侧修改设置。'}
                </div>
            )}

            <style jsx>{`
                .main-container {
                    display: flex;
                    height: 100vh;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }

                .sidebar-nav {
                    flex: 0 0 64px;
                    min-width: 64px;
                    max-width: 64px;
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-right: 1px solid rgba(255, 255, 255, 0.2);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    padding: 20px 0;
                    gap: 16px;
                    box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
                }

                .user-avatar-button {
                    width: 44px;
                    height: 44px;
                    border-radius: 50%;
                    overflow: hidden;
                    border: 2px solid #667eea;
                    padding: 0;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
                    display: block;
                }

                .user-avatar-button:hover {
                    transform: scale(1.05);
                    box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
                }

                .user-avatar {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }

                .nav-button {
                    width: 44px;
                    height: 44px;
                    border-radius: 12px;
                    border: none;
                    background: rgba(255, 255, 255, 0.8);
                    display: grid;
                    place-items: center;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }

                .nav-button:hover {
                    background: rgba(255, 255, 255, 0.9);
                    transform: translateY(-2px);
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                }

                .nav-button.active {
                    background: rgba(102, 126, 234, 0.15);
                    border: 2px solid #667eea;
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                }

                .nav-icon {
                    width: 24px;
                    height: 24px;
                    object-fit: contain;
                    filter: brightness(1.2);
                    transition: all 0.3s ease;
                }

                .nav-button.active .nav-icon {
                    filter: brightness(1.2) drop-shadow(0 0 3px rgba(102, 126, 234, 0.5));
                }

                .sidebar-panel {
                    flex: 0 0 ${sidebarWidth}px;
                    width: ${sidebarWidth}px;
                    min-width: 250px;
                    max-width: 500px;
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-right: 1px solid rgba(255, 255, 255, 0.2);
                    display: flex;
                    flex-direction: column;
                    box-sizing: border-box;
                    overflow: hidden;
                    box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
                    position: relative;
                }
                
                .resize-handle {
                    position: absolute;
                    right: 0;
                    top: 0;
                    width: 5px;
                    height: 100%;
                    cursor: col-resize;
                    background: transparent;
                    z-index: 10;
                    transition: background 0.2s ease;
                }
                
                .resize-handle:hover {
                    background: rgba(102, 126, 234, 0.3);
                }
                
                .resize-handle:active {
                    background: rgba(102, 126, 234, 0.5);
                }

                .search-container {
                    padding: 16px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
                }

                .panel-content {
                    flex: 1;
                    overflow: auto;
                    padding: 16px;
                }

                .empty-state {
                    flex: 1;
                    display: grid;
                    place-items: center;
                    color: rgba(255, 255, 255, 0.8);
                    font-size: 18px;
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(5px);
                }
                
                /* 确保聊天区域有正确的层级 */
                .main-container > div:last-child {
                    position: relative;
                    z-index: 2;
                }
                
                .user-avatar-placeholder {
                    width: 100%;
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    font-weight: 700;
                    font-size: 18px;
                }
            `}</style>
        </div>
    );
}
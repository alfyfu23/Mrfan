import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useUserContext } from '@/context/UserContext';
import { BACKEND_URL } from '@/constant/strings';

interface UserTooltipProps {
    user: {
        id: number;
        nickname?: string;
        username?: string;
        avatar?: string;
        is_online?: boolean;
        is_active?: boolean;
        info?: string;
    };
    children: React.ReactNode;
}

export default function UserTooltip({ user, children }: UserTooltipProps) {
    const { token, id_to_username, update_id_to_username, isUserOnline } = useUserContext();
    const containerRef = useRef<HTMLDivElement>(null);
    const [isVisible, setIsVisible] = useState(false);
    const [position, setPosition] = useState({ top: 0, left: 0 });
    const [isMounted, setIsMounted] = useState(false);
    const lastFetchRef = useRef<Record<number, number>>({});

    useEffect(() => { setIsMounted(true); }, []);

    const fetchLatestProfile = useCallback(async () => {
        if (!token || !user?.id) return;
        const last = lastFetchRef.current[user.id];
        if (last && Date.now() - last < 15000) return; // 避免频繁请求
        try {
            const resp = await fetch(`https://${BACKEND_URL}/account/get_info?target=${user.id}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const d = await resp.json();
            if (d?.code === 0) {
                const normAvatar = d.avatar && typeof d.avatar === 'string' && d.avatar.startsWith('/')
                    ? `https://${BACKEND_URL}${d.avatar}`
                    : d.avatar;
                update_id_to_username(user.id, {
                    id: user.id,
                    name: d.username,
                    avatar: normAvatar || undefined,
                    info: d.info,
                    is_active: d.is_active
                });
            }
        } catch (err) {
            console.warn('加载用户信息失败', err);
        } finally {
            lastFetchRef.current[user.id] = Date.now();
        }
    }, [token, update_id_to_username, user?.id]);

    const handleMouseEnter = () => {
        if (!containerRef.current || typeof window === 'undefined') return;
        
        const containerRect = containerRef.current.getBoundingClientRect();
        
        // 计算悬浮窗口的位置
        let left = containerRect.right + 10;
        let top = containerRect.top;
        
        // 估算悬浮窗口的尺寸
        const tooltipWidth = 220;
        const tooltipHeight = 120;
        
        // 确保悬浮窗口不会超出视口右侧
        if (left + tooltipWidth > window.innerWidth) {
            left = containerRect.left - tooltipWidth - 10;
        }
        
        // 确保悬浮窗口不会超出视口底部
        if (top + tooltipHeight > window.innerHeight) {
            top = window.innerHeight - tooltipHeight - 10;
        }
        
        // 确保悬浮窗口不会超出视口顶部
        if (top < 10) {
            top = 10;
        }
        
        setPosition({ top, left });
        setIsVisible(true);
        void fetchLatestProfile();
    };

    const handleMouseLeave = () => {
        setIsVisible(false);
    };

    useEffect(() => {
        if (isVisible) {
            void fetchLatestProfile();
        }
    }, [isVisible, fetchLatestProfile]);

    const mergedProfile = useMemo(() => {
        const cached = user.id ? id_to_username[user.id] : undefined;
        const displayName = cached?.name || user.nickname || user.username || '未知用户';
        const username = cached?.name || user.username || user.nickname || '未知用户';
        const signature = cached?.info ?? user.info;
        const avatar = cached?.avatar || user.avatar;
        const isActive = cached?.is_active ?? user.is_active;
        const online = user.id ? isUserOnline(user.id) : user.is_online;
        return { displayName, username, signature, avatar, isActive, online };
    }, [id_to_username, isUserOnline, user]);

    const tooltipNode = (isMounted && isVisible) ? createPortal(
        <div className="user-tooltip-popover" style={{ top: position.top, left: position.left }}>
            <div className="user-tooltip-username">{mergedProfile.displayName}</div>
            <div className="user-tooltip-details">
                {mergedProfile.isActive === false ? (
                    <div className="user-tooltip-item" style={{ color: 'red', fontWeight: 'bold' }}>
                        已注销
                    </div>
                ) : (
                    <div className="user-tooltip-item">
                        <span className={`user-tooltip-status ${mergedProfile.online ? 'online' : 'offline'}`}></span>
                        {mergedProfile.online ? '在线' : '离线'}
                    </div>
                )}
                {mergedProfile.signature ? (
                    <div className="user-tooltip-item signature-text">{mergedProfile.signature}</div>
                ) : (
                    <div className="user-tooltip-item signature-text muted">这个人很神秘，什么也没写</div>
                )}
                {mergedProfile.username && (
                    <div className="user-tooltip-item">用户名: {mergedProfile.username}</div>
                )}
            </div>
        </div>,
        document.body
    ) : null;

    return (
        <div
            ref={containerRef}
            className="user-tooltip-container"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            {children}
            {tooltipNode}

            {isMounted && (
                <style jsx>{`
                    .user-tooltip-container {
                        position: relative;
                        display: inline-block;
                    }
                `}</style>
            )}
            
            {isMounted && (
                <style jsx global>{`
                    .user-tooltip-popover {
                        position: fixed;
                        background: rgba(255, 255, 255, 0.98);
                        border: 1px solid rgba(102, 126, 234, 0.25);
                        border-radius: 12px;
                        padding: 12px 16px;
                        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.18);
                        z-index: 2147483647;
                        min-width: 220px;
                        white-space: nowrap;
                        pointer-events: auto;
                    }

                    .user-tooltip-username {
                        font-weight: 600;
                        font-size: 16px;
                        color: #111;
                        margin-bottom: 10px;
                        padding-bottom: 8px;
                        border-bottom: 1px solid rgba(0, 0, 0, 0.08);
                    }

                    .user-tooltip-details {
                        display: flex;
                        flex-direction: column;
                        gap: 6px;
                    }

                    .user-tooltip-item {
                        font-size: 14px;
                        color: #374151;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }

                    .user-tooltip-item.signature-text {
                        line-height: 1.4;
                        white-space: normal;
                        max-width: 260px;
                    }

                    .user-tooltip-item.signature-text.muted {
                        color: #6b7280;
                    }

                    .user-tooltip-status {
                        width: 8px;
                        height: 8px;
                        border-radius: 50%;
                        display: inline-block;
                    }

                    .user-tooltip-status.online {
                        background-color: #10b981;
                    }

                    .user-tooltip-status.offline {
                        background-color: #6b7280;
                    }
                `}</style>
            )}
        </div>
    );
}
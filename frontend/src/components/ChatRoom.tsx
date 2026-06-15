import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import type { Member } from "@/types/User";
import { Message } from "@/types/Message";
import { useUserContext } from "@/context/UserContext";
import { BACKEND_URL } from "@/constant/strings";
import { toast } from "react-toastify";
import GroupInfoPanel from './GroupInfoPanel';
import UserTooltip from './UserTooltip';
import Avatar from './Avatar';
import { getSecondaryTextColor } from '@/utils/themeDetector';

const isImageLike = (type?: string, text?: string) => {
    if (type === 'image') return true;
    return typeof text === 'string' && /(\.png|\.jpg|\.jpeg|\.gif|\.webp)(\?.*)?$/i.test(text.trim());
};

const isAudioLike = (type?: string, text?: string) => {
    if (type === 'audio') return true;
    return typeof text === 'string' && /(\.mp3|\.wav|\.m4a|\.aac|\.ogg)(\?.*)?$/i.test(text.trim());
};

const isVideoLike = (type?: string, text?: string) => {
    if (type === 'video') return true;
    return typeof text === 'string' && /(\.mp4|\.webm|\.mov|\.mkv|\.avi)(\?.*)?$/i.test(text.trim());
};

const resolveMediaUrl = (url?: string) => {
    if (!url) return '';
    return url.startsWith('/') ? `https://${BACKEND_URL}${url}` : url;
};

const formatAudioDuration = (seconds: number) => {
    if (!Number.isFinite(seconds) || seconds <= 0) return null;
    const totalSeconds = Math.round(seconds);
    const minutes = Math.floor(totalSeconds / 60);
    const remainingSeconds = totalSeconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

type MessageMenuState = {
    message: Message;
    position: { left: number; top: number };
    placement: 'above' | 'below';
};

const clampValue = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

export default function ChatBox({ conversationId }: { conversationId: number | null }) {
    const { username, selfId, conversations, ws, markConversationRead, searchHistory, deleteMessage, id_to_username, isUserOnline, mergeConversationMessages } = useUserContext();
    const [inputValue, setInputValue] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [audioDurationMap, setAudioDurationMap] = useState<Record<string, string | null>>({});
    const [videoThumbnailMap, setVideoThumbnailMap] = useState<Record<string, string | null>>({});
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);
    const [replyTo, setReplyTo] = useState<Message | null>(null);
    const lastReadKeyRef = useRef<string | null>(null);
    const markTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const prevConvIdRef = useRef<number | null>(null);
    const [editingMessage, setEditingMessage] = useState<Message | null>(null);
    const [messageMenu, setMessageMenu] = useState<MessageMenuState | null>(null);
    const [hoveredMessageId, setHoveredMessageId] = useState<number | null>(null);
    const [showEmojiPanel, setShowEmojiPanel] = useState(false);
    const [inputHeight, setInputHeight] = useState(240);
    const [isResizing, setIsResizing] = useState(false);
    const inputAreaRef = useRef<HTMLDivElement>(null);
    const [previewImage, setPreviewImage] = useState<string | null>(null);
    const [isComposing, setIsComposing] = useState(false);
    const [replyPreviewAudioDuration, setReplyPreviewAudioDuration] = useState<string | null>(null);
    const [historyPanelMessages, setHistoryPanelMessages] = useState<Message[]>([]);

    const requestVideoThumbnail = React.useCallback((url: string | undefined | null) => {
        if (!url) return;
        if (videoThumbnailMap[url] !== undefined) return;

        setVideoThumbnailMap(prev => ({ ...prev, [url]: null }));

        const videoEl = document.createElement('video');
        videoEl.crossOrigin = 'anonymous';
        videoEl.muted = true;
        videoEl.playsInline = true;
        videoEl.src = resolveMediaUrl(url);

        const cleanup = () => {
            videoEl.removeEventListener('loadedmetadata', handleLoadedMetadata);
            videoEl.removeEventListener('seeked', handleSeeked);
            videoEl.removeEventListener('error', handleError);
            videoEl.pause();
            videoEl.removeAttribute('src');
        };

        const captureFrame = () => {
            const canvas = document.createElement('canvas');
            const width = videoEl.videoWidth;
            const height = videoEl.videoHeight;
            if (!width || !height) {
                setVideoThumbnailMap(prev => ({ ...prev, [url]: null }));
                cleanup();
                return;
            }
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            if (!ctx) {
                setVideoThumbnailMap(prev => ({ ...prev, [url]: null }));
                cleanup();
                return;
            }
            ctx.drawImage(videoEl, 0, 0, width, height);
            const dataUrl = canvas.toDataURL('image/jpeg', 0.75);
            setVideoThumbnailMap(prev => ({ ...prev, [url]: dataUrl }));
            cleanup();
        };

        const handleSeeked = () => captureFrame();
        const handleLoadedMetadata = () => {
            try {
                const target = Math.min(0.1, Math.max(0, (videoEl.duration || 0))); // seek to near start
                videoEl.currentTime = target;
            } catch {
                captureFrame();
            }
        };
        const handleError = () => {
            setVideoThumbnailMap(prev => ({ ...prev, [url]: null }));
            cleanup();
        };

        videoEl.addEventListener('loadedmetadata', handleLoadedMetadata);
        videoEl.addEventListener('seeked', handleSeeked);
        videoEl.addEventListener('error', handleError);
        videoEl.load();
    }, [videoThumbnailMap]);

    const requestAudioDuration = React.useCallback((url: string | undefined | null) => {
        if (!url) return;
        const resolvedUrl = resolveMediaUrl(url);
        if (audioDurationMap[url] !== undefined) return;

        setAudioDurationMap(prev => ({ ...prev, [url]: null }));

        const audioEl = new Audio(resolvedUrl);
        const handleLoaded = () => {
            setAudioDurationMap(prev => ({ ...prev, [url]: formatAudioDuration(audioEl.duration) }));
            cleanup();
        };
        const handleError = () => {
            setAudioDurationMap(prev => ({ ...prev, [url]: null }));
            cleanup();
        };
        const cleanup = () => {
            audioEl.removeEventListener('loadedmetadata', handleLoaded);
            audioEl.removeEventListener('error', handleError);
            audioEl.pause();
            audioEl.removeAttribute('src');
        };
        audioEl.addEventListener('loadedmetadata', handleLoaded);
        audioEl.addEventListener('error', handleError);
    }, [audioDurationMap]);
    
    // 搜索相关状态
    const [showSearch, setShowSearch] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [searchSender, setSearchSender] = useState<number | 'inactive' | undefined>(undefined);
    const [searchDateStart, setSearchDateStart] = useState("");
    const [searchDateEnd, setSearchDateEnd] = useState("");
    const [searchResults, setSearchResults] = useState<Message[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [isLoadingFullHistory, setIsLoadingFullHistory] = useState(false);
    
    // 常用表情列表
    const commonEmojis = ['😀', '😃', '😄', '😁', '😅', '😂', '🤣', '😊', '😇', '🙂', '😉', '😌', '😍', '🥰', '😘', '😗', '😙', '😚', '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥', '😌', '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '🥵', '🥶', '🥴', '😵', '🤯', '🤠', '🥳', '😎', '🤓', '🧐', '😕', '😟', '🙁', '☹️', '😮', '😯', '😲', '😳', '🥺', '😦', '😧', '😨', '😰', '😥', '😢', '😭', '😱', '😖', '😣', '😞', '😓', '😩', '😫', '🥱', '😤', '😡', '😠', '🤬', '😈', '👿', '💀', '☠️', '💩', '🤡', '👹', '👺', '👻', '👽', '👾', '🤖', '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝', '👍', '👎', '👌', '✌️', '🤞', '🤟', '🤘', '🤙', '👈', '👉', '👆', '👇', '☝️', '✋', '🤚', '🖐️', '🖖', '👋', '🤙', '💪', '🙏'];
    
    const effectiveConvId = conversationId ?? null;
    const currentConv = conversations.find(item => item.id === effectiveConvId);
    const memberAvatarMap = React.useMemo(() => {
        const map = new Map<number, string>();
        currentConv?.member?.forEach(m => {
            if (m.avatar) map.set(m.id, m.avatar);
        });
        return map;
    }, [currentConv]);
    const canSendCurrentConversation = React.useMemo(() => {
        if (!currentConv) return false;
        if (!currentConv.isGroup) return true;
        if (!selfId) return false;
        const membership = currentConv.member?.find(m => m.id === selfId);
        if (!membership) return false;
        if (membership.is_active === false) return false;
        return true;
    }, [currentConv, selfId]);

    // 同步当前会话消息
    useEffect(() => {
        if (!effectiveConvId) { setMessages([]); return; }
        const conv = conversations.find(item => item.id === effectiveConvId);
        setMessages(conv?.messages ?? []);
        if (prevConvIdRef.current !== effectiveConvId) {
            setShowSearch(false);
            setSearchResults([]);
            prevConvIdRef.current = effectiveConvId;
        }
    }, [effectiveConvId, conversations]);

    // 滚动到底部
    useEffect(() => {
        if (!showSearch) {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, showSearch]);

    // 预加载回复音频的时长，供消息气泡和输入区复用
    useEffect(() => {
        const urls = new Set<string>();
        messages.forEach(m => {
            const rt = m.reply_to_message;
            if (rt && isAudioLike(rt.type, rt.text) && rt.text) {
                urls.add(rt.text);
            }
        });
        urls.forEach(url => requestAudioDuration(url));
    }, [messages, requestAudioDuration]);

    // 预加载视频缩略图（消息本身 + 回复目标）
    useEffect(() => {
        const urls = new Set<string>();
        messages.forEach(m => {
            if (isVideoLike(m.type, m.text) && m.text) urls.add(m.text);
            const rt = m.reply_to_message;
            if (rt && isVideoLike(rt.type, rt.text) && rt.text) {
                urls.add(rt.text);
            }
        });
        urls.forEach(url => requestVideoThumbnail(url));
    }, [messages, requestVideoThumbnail]);

    const mergeMessages = React.useCallback((existing: Message[], incoming: Message[]) => {
        const buildKey = (msg: Message) => (typeof msg.id === 'number' ? msg.id : `${msg.sender}-${msg.timestamp?.valueOf?.() ?? 0}-${msg.text ?? ''}`);
        const map = new Map<string | number, Message>();
        existing.forEach(m => map.set(buildKey(m), m));
        incoming.forEach(m => {
            const key = buildKey(m);
            const prevMsg = map.get(key);
            map.set(key, prevMsg ? { ...prevMsg, ...m } : m);
        });
        return Array.from(map.values()).sort((a, b) => {
            const at = a.timestamp ? a.timestamp.getTime() : 0;
            const bt = b.timestamp ? b.timestamp.getTime() : 0;
            return at - bt;
        });
    }, []);

    // 搜索功能
    const handleSearch = async () => {
        if (!effectiveConvId) return;
        setIsSearching(true);
        try {
            const senderParam = typeof searchSender === 'number' ? searchSender : undefined;
            const results = await searchHistory(
                effectiveConvId, 
                searchQuery, 
                senderParam, 
                searchDateStart ? new Date(searchDateStart).toISOString() : undefined,
                searchDateEnd ? new Date(searchDateEnd).toISOString() : undefined
            );
            const activeMemberIds = new Set(currentConv?.member?.map(m => m.id) ?? []);
            const filtered = searchSender === 'inactive'
                ? results.filter(msg => {
                    // 优先使用后端标记；若无标记，则以“不在当前成员列表”视为已退出
                    if (msg.sender_is_active === false) return true;
                    return !activeMemberIds.has(msg.sender);
                })
                : results;
            setSearchResults(filtered);
        } finally {
            setIsSearching(false);
        }
    };

    const handleLoadFullHistory = async () => {
        if (!effectiveConvId) return;
        setIsLoadingFullHistory(true);
        try {
            const history = await searchHistory(effectiveConvId);
            if (!history.length) {
                toast.info('暂无更多历史记录');
                return;
            }
            setHistoryPanelMessages(history);
            const merged = mergeMessages(messages, history);
            setMessages(merged);
            mergeConversationMessages(effectiveConvId, history);
        } catch (e) {
            console.error('加载历史记录失败', e);
            toast.error('加载历史记录失败');
        } finally {
            setIsLoadingFullHistory(false);
        }
    };

    // 删除消息
    const handleDeleteMessage = async (messageId: number) => {
        if (confirm("确定要删除这条消息吗？（仅对自己不可见）")) {
            await deleteMessage(messageId);
            setMessageMenu(null);
        }
    };

    // 滚动到指定消息
    const scrollToMessage = (messageId: number | null | undefined) => {
        if (!messageId) return;
        
        const messageElement = document.getElementById(`message-${messageId}`);
        if (messageElement) {
            messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // 高亮显示目标消息
            const allMessages = document.querySelectorAll('.message-bubble');
            allMessages.forEach(msg => msg.classList.remove('highlighted'));
            messageElement.classList.add('highlighted');
            
            // 3秒后移除高亮
            setTimeout(() => {
                messageElement.classList.remove('highlighted');
            }, 3000);
        }
    };


    // 已读上报（群聊/私聊一致，按会话+最后消息去抖去重）
    useEffect(() => {
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
        if (!token || !effectiveConvId || !currentConv) return;
        const unread = currentConv.unread_count ?? 0;
        if (unread <= 0) return;
        const lastMsg = messages.length ? messages[messages.length - 1] : undefined;
        const lastMsgId = typeof lastMsg?.id === 'number' ? lastMsg.id : -messages.length;
        const key = `${effectiveConvId}:${lastMsgId}`;
        if (lastReadKeyRef.current === key) return;
        if (markTimerRef.current) clearTimeout(markTimerRef.current);
        markTimerRef.current = setTimeout(async () => {
            try {
                // 先通过API标记已读
                await fetch(`https://${BACKEND_URL}/chat/message/read`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                    body: JSON.stringify({ conversation: effectiveConvId, up_to_id: lastMsgId })
                });
                markConversationRead(effectiveConvId);
                lastReadKeyRef.current = key;
                
                // 然后通过WebSocket发送已读状态更新，让其他用户实时看到
                if (ws && ws.readyState === WebSocket.OPEN && lastMsgId > 0) {
                    // 判断是否为私聊
                    const isPrivateChat = currentConv?.isGroup === false;
                    
                    if (isPrivateChat) {
                        // 私聊：发送私聊已读回执
                        ws.send(JSON.stringify({
                            type: 'read_receipt',
                            conversation: effectiveConvId,
                            message_id: lastMsgId,
                            reader_id: selfId
                        }));
                    } else {
                        // 群聊：发送群聊已读回执
                        ws.send(JSON.stringify({
                            type: 'read_receipt',
                            conversation: effectiveConvId,
                            message_id: lastMsgId
                        }));
                    }
                }
            } catch (e) { console.error('标记已读失败:', e); }
        }, 300);
        return () => { if (markTimerRef.current) clearTimeout(markTimerRef.current); };
    }, [effectiveConvId, messages, currentConv, markConversationRead, ws, selfId]);

    // 处理WebSocket错误消息
    useEffect(() => {
        if (!ws) return;
        
        const handleMessage = (event: MessageEvent) => {
            try {
                const data = JSON.parse(event.data);
                const optimisticErrorTypes = new Set([
                    'not_friends',
                    'not_group_member',
                    'not_in_group',
                    'not_member',
                    'not_in_conversation'
                ]);
                if (data.type === 'error' && optimisticErrorTypes.has(data.error)) {
                    // 显示用户友好的错误提示
                    if (data.error === 'not_member' || data.error === 'not_in_group' || data.error === 'not_group_member') {
                        toast.error('你已不在该群聊中，无法发送消息');
                    } else if (data.error === 'not_friends' || data.error === 'not_in_conversation') {
                        toast.error('当前会话不可用，无法发送消息');
                    } else {
                        toast.error('发送消息失败，请稍后重试');
                    }
                    
                    // 移除刚刚添加的临时消息（如果存在）
                    setMessages(prev => {
                        if (prev.length > 0) {
                            const lastMsg = prev[prev.length - 1];
                            // 如果最后一条消息是当前用户发送的，并且是刚刚发送的（时间戳在最近5秒内）
                            const now = new Date();
                            const msgTime = new Date(lastMsg.timestamp);
                            const timeDiff = (now.getTime() - msgTime.getTime()) / 1000;
                            
                            if (lastMsg.sender === selfId && timeDiff < 5) {
                                return prev.slice(0, -1); // 移除最后一条消息
                            }
                        }
                        return prev;
                    });
                }
            } catch (e) {
                console.error('解析WebSocket消息失败:', e);
            }
        };
        
        ws.addEventListener('message', handleMessage);
        
        return () => {
            ws.removeEventListener('message', handleMessage);
        };
    }, [ws, selfId]);

    // 发送消息
    async function send_message(text: string) {
        const convIdToUse = effectiveConvId;
        if (!convIdToUse || !text.trim()) return;
        if (!canSendCurrentConversation) {
            toast.error(currentConv?.isGroup ? '你已不在该群聊，无法发送消息' : '当前会话不可用');
            return;
        }
        if (!ws || ws.readyState !== WebSocket.OPEN) { console.error("WebSocket 未连接"); return; }
        try {
            ws.send(JSON.stringify({ type: 'message', conversation: convIdToUse, message: { content: text, type: 'text', reply_to: replyTo?.id } }));
            const tempMsg: Message = {
                sender: selfId ?? 0,
                nickname: username ?? "",
                text,
                type: 'text',
                reply_to: replyTo?.id,
                timestamp: new Date(),
                read_by: selfId ? [selfId] : [],
                is_read: undefined  // 发送的消息初始状态为未读，等待对方已读回执
            };
            setMessages(prev => [...prev, tempMsg]); setInputValue(""); setReplyTo(null);
        } catch (e) {
            console.error('发送失败', e);
            // 显示错误提示
            if (e instanceof Error) {
                // 这里可以添加更具体的错误处理
                console.error('发送消息失败:', e.message);
            }
            
            // 移除刚刚添加的临时消息（如果存在）
            setMessages(prev => {
                if (prev.length > 0) {
                    const lastMsg = prev[prev.length - 1];
                    // 如果最后一条消息是当前用户发送的，并且是刚刚发送的（时间戳在最近5秒内）
                    const now = new Date();
                    const msgTime = new Date(lastMsg.timestamp);
                    const timeDiff = (now.getTime() - msgTime.getTime()) / 1000;
                    
                    if (lastMsg.sender === selfId && timeDiff < 5) {
                        return prev.slice(0, -1); // 移除最后一条消息
                    }
                }
                return prev;
            });
        }
    }

    // 编辑消息
    async function edit_message(messageId: number, newContent: string) {
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
        if (!token || !effectiveConvId) return;
        
        try {
            const response = await fetch(`https://${BACKEND_URL}/chat/message/edit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ id: messageId, content: newContent })
            });
            
            const data = await response.json();
            
            if (response.ok && data.code === 0) {
                // 通过WebSocket发送编辑消息
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'edit_message',
                        conversation: effectiveConvId,
                        message_id: messageId,
                        content: newContent
                    }));
                }
                setEditingMessage(null);
            } else {
                console.error('编辑消息失败:', data.info || '未知错误');
            }
        } catch (e) { console.error('编辑消息失败', e); }
    }

    // 撤回消息
    async function recall_message(messageId: number) {
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
        if (!token || !effectiveConvId) return;
        
        try {
            const response = await fetch(`https://${BACKEND_URL}/chat/message/recall`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ id: messageId })
            });
            
            const data = await response.json();
            
            if (response.ok && data.code === 0) {
                // 通过WebSocket发送撤回消息
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'recall_message',
                        conversation: effectiveConvId,
                        message_id: messageId
                    }));
                }
                setMessageMenu(null);
            } else {
                console.error('撤回消息失败:', data.info || '未知错误');
                setMessageMenu(null);
            }
        } catch (e) {
            console.error('撤回消息失败', e);
            setMessageMenu(null);
        }
    }

    // 显示消息操作菜单
    function show_message_menu(event: React.MouseEvent<HTMLDivElement>, message: Message) {
        event.preventDefault();
        event.stopPropagation();
        const bubble = event.currentTarget;
        const rect = bubble.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const centerX = rect.left + rect.width / 2;
        const safeLeft = clampValue(centerX, 72, viewportWidth - 72);
        const spaceBelow = viewportHeight - rect.bottom;
        const spaceAbove = rect.top;
        const preferredPlacement: 'above' | 'below' = spaceBelow >= 80 || spaceBelow >= spaceAbove ? 'below' : 'above';
        const positionTop = preferredPlacement === 'below' ? rect.bottom : rect.top;
        setMessageMenu({
            message,
            position: { left: safeLeft, top: positionTop },
            placement: preferredPlacement
        });
    }

    // 隐藏消息操作菜单
    function hide_message_menu() {
        setMessageMenu(null);
    }

    // 点击外部区域隐藏菜单
    useEffect(() => {
        const handleClick = (event: MouseEvent) => {
            if (event.button === 2) return;
            hide_message_menu();
        };
        const handleScroll = () => hide_message_menu();
        const handleResize = () => hide_message_menu();
        document.addEventListener('click', handleClick);
        window.addEventListener('scroll', handleScroll, true);
        window.addEventListener('resize', handleResize);
        return () => {
            document.removeEventListener('click', handleClick);
            window.removeEventListener('scroll', handleScroll, true);
            window.removeEventListener('resize', handleResize);
        };
    }, []);
    
    // 点击外部区域关闭表情面板
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (showEmojiPanel) {
                const target = event.target as Element;
                if (!target.closest('.emoji-panel') && !target.closest('.emoji-button')) {
                    setShowEmojiPanel(false);
                }
            }
        };
        
        document.addEventListener('click', handleClickOutside);
        return () => {
            document.removeEventListener('click', handleClickOutside);
        };
    }, [showEmojiPanel]);
    
    // 处理输入容器大小调整
    useEffect(() => {
        const handleMouseMove = (e: any) => {
            if (!isResizing || !inputAreaRef.current) return;
            
            inputAreaRef.current.getBoundingClientRect();
            const newHeight = Math.max(60, Math.min(300, window.innerHeight - e.clientY));
            setInputHeight(newHeight);
        };
        
        const handleMouseUp = () => {
            setIsResizing(false);
        };
        
        if (isResizing) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            return () => {
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
            };
        }
    }, [isResizing, inputHeight]);

    const replyPreviewIsImage = isImageLike(replyTo?.type, replyTo?.text);
    const replyPreviewIsAudio = isAudioLike(replyTo?.type, replyTo?.text);
    const replyPreviewIsVideo = isVideoLike(replyTo?.type, replyTo?.text);
    const replyPreviewVideoThumb = replyPreviewIsVideo && replyTo?.text ? videoThumbnailMap[replyTo.text] : null;
    const replyPreviewText = replyTo?.type === 'file'
        ? '[文件]'
        : replyPreviewIsAudio
            ? `[语音${replyPreviewAudioDuration ? ` · ${replyPreviewAudioDuration}` : ''}]`
            : replyPreviewIsVideo
                ? '[视频]'
            : replyPreviewIsImage
                ? '[图片]'
                : (replyTo?.text || '').length > 30
                    ? (replyTo?.text || '').substring(0, 30) + '...'
                    : (replyTo?.text || '');

    useEffect(() => {
        let audioEl: HTMLAudioElement | null = null;
        let canceled = false;

        if (replyPreviewIsAudio && replyTo?.text) {
            const cached = audioDurationMap[replyTo.text];
            if (cached !== undefined) {
                setReplyPreviewAudioDuration(cached);
            } else {
                audioEl = new Audio(resolveMediaUrl(replyTo.text));
                const handleLoaded = () => {
                    if (canceled) return;
                    const formatted = formatAudioDuration(audioEl?.duration ?? 0);
                    setReplyPreviewAudioDuration(formatted);
                    setAudioDurationMap(prev => ({ ...prev, [replyTo.text as string]: formatted }));
                };
                const handleError = () => {
                    if (canceled) return;
                    setReplyPreviewAudioDuration(null);
                    setAudioDurationMap(prev => ({ ...prev, [replyTo.text as string]: null }));
                };
                audioEl.addEventListener('loadedmetadata', handleLoaded);
                audioEl.addEventListener('error', handleError);
            }
        } else {
            setReplyPreviewAudioDuration(null);
        }

        return () => {
            canceled = true;
            if (audioEl) {
                audioEl.pause();
                audioEl.removeAttribute('src');
                audioEl.load();
                audioEl = null;
            }
        };
    }, [audioDurationMap, replyPreviewIsAudio, replyTo]);

    // 预加载当前输入框回复目标的视频缩略图
    useEffect(() => {
        if (replyPreviewIsVideo && replyTo?.text) {
            requestVideoThumbnail(replyTo.text);
        }
    }, [replyPreviewIsVideo, replyTo, requestVideoThumbnail]);
    
    const isPrivateChatHeader = currentConv?.isGroup === false;
    const otherMember = isPrivateChatHeader ? currentConv?.member?.find(m => m.id !== selfId) : undefined;
    const showDeactivatedBadge = otherMember?.is_active === false;
    const otherMemberOnline = otherMember ? isUserOnline(otherMember.id) : false;

    return (
        <div className="chat-container">
            {/* Header */}
            <div className="chat-header">
                <div className="chat-header-info">
                    <div className="chat-avatar">
                        {currentConv?.avatar ? <img src={currentConv.avatar.startsWith('/') ? `https://${BACKEND_URL}${currentConv.avatar}` : currentConv.avatar} alt="avatar" className="chat-avatar-image" /> : <span className="chat-avatar-placeholder">{currentConv?.name?.charAt(0) ?? "?"}</span>}
                    </div>
                    <div className="chat-header-details">
                        <div className="chat-title">
                            {currentConv?.name ?? "选择一个聊天"}
                            {showDeactivatedBadge && <span style={{ color: '#dc2626', fontSize: 12, marginLeft: 8 }}>(已注销)</span>}
                        </div>
                        <div className="chat-status">{isPrivateChatHeader ? (otherMemberOnline ? "在线" : "离线") : ""}</div>
                    </div>
                </div>
                {effectiveConvId !== null && (
                    <GroupMore
                        convId={effectiveConvId}
                        convName={currentConv?.name}
                        convAvatar={currentConv?.avatar}
                        membersCount={currentConv?.member?.length ?? 0}
                        isGroup={currentConv?.isGroup}
                        onOpenSearch={() => setShowSearch(true)}
                        onLoadFullHistory={handleLoadFullHistory}
                        loadingHistory={isLoadingFullHistory}
                        historyMessages={historyPanelMessages}
                    />
                )}
            </div>

            {/* Messages */}
            <div className="messages-container">
                <div className="messages-list">
                    {messages.map((message, i) => {
                        const isMine = (selfId != null) ? (message.sender === selfId) : (message.nickname === username);
                        const isImage = isImageLike(message.type, message.text);
                        const isAudio = isAudioLike(message.type, message.text);
                        const isVideo = isVideoLike(message.type, message.text);
                        const senderMember = currentConv?.member?.find(m => m.id === message.sender);
                        const senderInfo = id_to_username[message.sender];
                        const senderAvatar = senderInfo?.avatar || senderMember?.avatar || memberAvatarMap.get(message.sender);
                        const senderDisplayName = senderInfo?.name || message.nickname || senderMember?.nickname || senderMember?.display_username || '用户';
                        const senderInitial = senderDisplayName ? senderDisplayName.charAt(0) : '?';
                        const replyTarget = message.reply_to_message;
                        const replyIsImage = isImageLike(replyTarget?.type, replyTarget?.text);
                        const replyIsAudio = isAudioLike(replyTarget?.type, replyTarget?.text);
                        const replyIsVideo = isVideoLike(replyTarget?.type, replyTarget?.text);
                        const replyAudioDuration = replyIsAudio && replyTarget?.text ? audioDurationMap[replyTarget.text] : null;
                        const replyVideoThumb = replyIsVideo && replyTarget?.text ? videoThumbnailMap[replyTarget.text] : null;
                        const replyTextContent = replyTarget?.type === 'file'
                            ? '[文件]'
                            : replyIsAudio
                                ? `[语音${replyAudioDuration ? ` · ${replyAudioDuration}` : ''}]`
                                : replyIsVideo
                                    ? '[视频]'
                                : replyIsImage
                                    ? '[图片]'
                                    : (replyTarget?.text || '').length > 20
                                        ? (replyTarget?.text || '').substring(0, 20) + '...'
                                        : (replyTarget?.text || '');
                        const avatarNode = (
                            <UserTooltip user={{
                                id: message.sender,
                                nickname: senderInfo?.name || message.nickname || senderMember?.nickname,
                                username: senderInfo?.name || senderMember?.display_username || senderMember?.nickname || message.nickname,
                                avatar: senderInfo?.avatar || senderAvatar,
                                is_online: isUserOnline(message.sender),
                                is_active: senderMember?.is_active,
                                info: senderInfo?.info
                            }}>
                                <div className="message-avatar">
                                    <Avatar
                                        src={senderAvatar?.startsWith('/') ? `https://${BACKEND_URL}${senderAvatar}` : senderAvatar}
                                        size={36}
                                        alt={senderDisplayName}
                                        fallbackText={senderInitial}
                                        className="message-avatar-image"
                                    />
                                </div>
                            </UserTooltip>
                        );
        // 判断是否为群聊
        const isGroupChat = currentConv?.isGroup === true;
        const showReceipt = isMine && isGroupChat;
        const showPrivateReadStatus = isMine && !isGroupChat;
        
        // 计算该消息被回复的次数
        const replyCount = messages.filter(m => m.reply_to === message.id).length;
        
        // 计算私聊对方是否已读
        const isPeerRead = message.read_by?.some(id => id !== selfId) ?? false;

        // 检查是否是系统消息（撤回提示）
        const isSystemMessage = message.type === 'system';
        
        // 格式化消息时间
        const formatMessageTime = (timestamp: Date) => {
            const now = new Date();
            const msgDate = new Date(timestamp);
            const diffInHours = (now.getTime() - msgDate.getTime()) / (1000 * 60 * 60);
            
            if (diffInHours < 24) {
                // 今天显示时间
                return msgDate.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
            } else {
                // 超过一天显示日期和时间
                return msgDate.toLocaleString('zh-CN', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            }
        };
                        
                        // 获取发送者的群昵称
                        const senderGroupNickname = senderMember?.nickname || senderInfo?.name || message.nickname;
                        
                        return (
                            <div key={i} className={`message-wrapper ${isSystemMessage ? 'system' : (isMine ? 'mine' : 'theirs')}`}>
                                <div className="message-content">
                                    {!isMine && !isSystemMessage && (
                                        <div className="message-avatar-container">
                                            {avatarNode}
                                            {/* 在群聊中显示发送者昵称 */}
                                            {isGroupChat && (
                                                <div className="sender-nickname">
                                                    {senderGroupNickname}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    {/* 对于自己的消息，创建一个容器来包含已读/未读标志和时间显示 */}
                                    {isMine && (showReceipt || showPrivateReadStatus || hoveredMessageId === message.id) && !isSystemMessage && (
                                        <div className="message-status-container">
                                            {/* 时间显示 - 使用绝对定位 */}
                                            {hoveredMessageId === message.id && (
                                                <div className="message-time-display">
                                                    {formatMessageTime(message.timestamp)}
                                                </div>
                                            )}
                                            {/* 已读/未读标志 */}
                                            {showReceipt && <div className="message-receipt"><ReadReceipt total={currentConv?.member?.length ?? 0} readBy={message.read_by ?? []} members={currentConv?.member ?? []} senderId={message.sender} /></div>}
                                            {showPrivateReadStatus && <div className="private-read-status"><PrivateReadStatus isRead={isPeerRead} /></div>}
                                        </div>
                                    )}
                                    <div className={`message-bubble ${isSystemMessage ? 'system' : (isMine ? 'mine' : 'theirs')}`} id={`message-${message.id}`}
                                          onContextMenu={(e) => {
                                                  if (!isSystemMessage) {
                                                      show_message_menu(e, message);
                                                  }
                                              }}
                                          onMouseEnter={() => setHoveredMessageId(message.id ?? null)}
                                          onMouseLeave={() => setHoveredMessageId(null)}
                                      >
                                        {/* 对于别人的消息，时间显示直接放在消息气泡内部 */}
                                        {!isMine && hoveredMessageId === message.id && !isSystemMessage && (
                                            <div className="message-time-display-others">
                                                {formatMessageTime(message.timestamp)}
                                            </div>
                                        )}
                                        {message.reply_to && (
                                            <div className="message-reply" onClick={() => scrollToMessage(message.reply_to)}>
                                                {message.reply_to_message ? (
                                                    <div className="reply-content">
                                                        <span className="reply-sender">{message.reply_to_message.sender_nickname || message.reply_to_message.nickname}:</span>
                                                        {replyIsImage ? (
                                                            <div className="reply-thumb">
                                                                <img src={resolveMediaUrl(message.reply_to_message.text)} alt="reply image" />
                                                            </div>
                                                        ) : replyIsVideo && replyVideoThumb ? (
                                                            <div className="reply-thumb video-thumb">
                                                                <img src={replyVideoThumb} alt="reply video" />
                                                            </div>
                                                        ) : (
                                                            <span className="reply-text">{replyTextContent}</span>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <span className="reply-fallback">被回复的消息已撤回</span>
                                                )}
                                            </div>
                                        )}
                                        {isImage ? (
                                            <div>
                                                <img
                                                    src={resolveMediaUrl(message.text)}
                                                    alt="image"
                                                    className="message-image"
                                                    onClick={() => setPreviewImage(resolveMediaUrl(message.text))}
                                                    onLoad={(e) => { e.currentTarget.nextElementSibling?.classList.add('hidden'); }}
                                                    onError={(e) => { e.currentTarget.style.display='none'; const errorDiv = e.currentTarget.nextElementSibling as HTMLElement; if (errorDiv) { errorDiv.classList.remove('hidden'); errorDiv.style.display='block'; } }}
                                                />
                                                <div className="message-image-error hidden">图片加载失败</div>
                                            </div>
                                        ) : isAudio ? (
                                            <audio controls src={resolveMediaUrl(message.text)} className="message-audio">
                                                您的浏览器不支持音频播放。
                                            </audio>
                                        ) : isVideo ? (
                                            <video
                                                controls
                                                src={resolveMediaUrl(message.text)}
                                                className="message-video"
                                                preload="metadata"
                                                poster={message.text ? videoThumbnailMap[message.text] ?? undefined : undefined}
                                                style={{ maxWidth: '320px', width: '100%', borderRadius: '8px' }}
                                            >
                                                您的浏览器不支持视频播放。
                                            </video>
                                        ) : message.type === 'file' ? (<a href={message.text && message.text.startsWith('/') ? `https://${BACKEND_URL}${message.text}` : message.text || ''} target="_blank" rel="noreferrer" className="message-file-link">打开文件</a>) : (message.text || '')}
                                        {message.is_edited && !isSystemMessage && <span className="message-edited">（已编辑）</span>}
                                        {replyCount > 0 && !isSystemMessage && (
                                            <div
                                                className="message-reply-count-indicator"
                                                style={{
                                                    color: isMine
                                                        ? 'rgba(255, 255, 255, 0.9)'
                                                        : getSecondaryTextColor()
                                                }}
                                            >
                                                {replyCount} 条回复
                                            </div>
                                        )}
                                    </div>
                                    {isMine && !isSystemMessage && avatarNode}
                                </div>
                            </div>
                        );
                    })}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {previewImage && (
                <div className="image-preview-backdrop" onClick={() => setPreviewImage(null)}>
                    <div className="image-preview-body" onClick={(e) => e.stopPropagation()}>
                        <img src={previewImage} alt="preview" className="image-preview-img" />
                        <button className="image-preview-close" onClick={() => setPreviewImage(null)}>×</button>
                    </div>
                </div>
            )}

            {/* Message Menu - 使用 Portal 渲染到 body 以避免 backdrop-filter 影响 fixed 定位 */}
            {messageMenu && typeof document !== 'undefined' && createPortal(
                <div
                    className="message-menu-portal"
                    style={{
                        position: 'fixed',
                        left: `${messageMenu.position.left}px`,
                        top: `${messageMenu.position.top}px`,
                        transform: messageMenu.placement === 'above'
                            ? 'translate(-50%, calc(-100% - 12px))'
                            : 'translate(-50%, 12px)',
                        zIndex: 2147483647,
                        background: '#fff',
                        border: '1px solid rgba(15, 23, 42, 0.08)',
                        borderRadius: '999px',
                        boxShadow: '0 24px 60px rgba(15, 23, 42, 0.25)',
                        padding: '6px 12px',
                        display: 'inline-flex',
                        gap: '8px',
                        alignItems: 'center',
                        pointerEvents: 'auto'
                    }}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div 
                        style={{
                            padding: '6px 14px',
                            cursor: 'pointer',
                            borderRadius: '999px',
                            transition: 'background 0.2s ease, color 0.2s ease',
                            color: '#0f172a',
                            fontSize: '14px',
                            fontWeight: 500,
                            whiteSpace: 'nowrap'
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(102, 126, 234, 0.12)'; e.currentTarget.style.color = '#4c1d95'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#0f172a'; }}
                        onClick={() => { setReplyTo(messageMenu.message); setMessageMenu(null); }}
                    >
                        回复
                    </div>
                    {((selfId != null) ? (messageMenu.message.sender === selfId) : (messageMenu.message.nickname === username)) && (
                        <>
                            <div 
                                style={{
                                    padding: '6px 14px',
                                    cursor: 'pointer',
                                    borderRadius: '999px',
                                    transition: 'background 0.2s ease, color 0.2s ease',
                                    color: '#0f172a',
                                    fontSize: '14px',
                                    fontWeight: 500,
                                    whiteSpace: 'nowrap'
                                }}
                                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(102, 126, 234, 0.12)'; e.currentTarget.style.color = '#4c1d95'; }}
                                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#0f172a'; }}
                                onClick={() => { setEditingMessage(messageMenu.message); setMessageMenu(null); }}
                            >
                                编辑
                            </div>
                            <div 
                                style={{
                                    padding: '6px 14px',
                                    cursor: 'pointer',
                                    borderRadius: '999px',
                                    transition: 'background 0.2s ease, color 0.2s ease',
                                    color: '#ef4444',
                                    fontSize: '14px',
                                    fontWeight: 500,
                                    whiteSpace: 'nowrap'
                                }}
                                onMouseEnter={(e) => { e.currentTarget.style.background = 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)'; e.currentTarget.style.color = '#dc2626'; }}
                                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#ef4444'; }}
                                onClick={() => { if (messageMenu.message.id) { recall_message(messageMenu.message.id); } setMessageMenu(null); }}
                            >
                                撤回
                            </div>
                        </>
                    )}
                    <div 
                        style={{
                            padding: '6px 14px',
                            cursor: 'pointer',
                            borderRadius: '999px',
                            transition: 'background 0.2s ease, color 0.2s ease',
                            color: '#ef4444',
                            fontSize: '14px',
                            fontWeight: 500,
                            whiteSpace: 'nowrap'
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)'; e.currentTarget.style.color = '#dc2626'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#ef4444'; }}
                        onClick={() => { if (messageMenu.message.id) { handleDeleteMessage(messageMenu.message.id); } }}
                    >
                        删除
                    </div>
                </div>,
                document.body
            )}

            {/* Search Modal */}
            {showSearch && (
                <div className="search-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowSearch(false); }}>
                    <div className="search-modal">
                        <div className="search-header">
                            <h3>查找聊天记录</h3>
                            <button className="search-close" onClick={() => setShowSearch(false)}>×</button>
                        </div>
                        <div className="search-filters">
                            <input 
                                type="text" 
                                placeholder="搜索关键词..." 
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="search-input"
                            />
                            {currentConv?.isGroup && (
                                <select 
                                    value={searchSender === 'inactive' ? 'inactive' : (searchSender || '')} 
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        if (!val) return setSearchSender(undefined);
                                        if (val === 'inactive') return setSearchSender('inactive');
                                        const num = Number(val);
                                        return setSearchSender(Number.isFinite(num) ? num : undefined);
                                    }}
                                    className="search-select"
                                >
                                    <option value="">所有成员</option>
                                    <option value="inactive">已退出成员</option>
                                    {currentConv.member?.map(m => (
                                        <option key={m.id} value={m.id}>{m.nickname}</option>
                                    ))}
                                </select>
                            )}
                            <div className="search-date-range">
                                <input 
                                    type="date" 
                                    value={searchDateStart}
                                    onChange={(e) => setSearchDateStart(e.target.value)}
                                    className="search-date"
                                />
                                <span>-</span>
                                <input 
                                    type="date" 
                                    value={searchDateEnd}
                                    onChange={(e) => setSearchDateEnd(e.target.value)}
                                    className="search-date"
                                />
                            </div>
                            <button onClick={handleSearch} className="search-btn" disabled={isSearching}>
                                {isSearching ? '搜索中...' : '搜索'}
                            </button>
                            <button onClick={handleLoadFullHistory} className="search-btn" disabled={isLoadingFullHistory}>
                                {isLoadingFullHistory ? '加载中...' : '加载全部历史'}
                            </button>
                        </div>
                        <div className="search-results">
                            {searchResults.length === 0 ? (
                                <div className="search-empty">暂无搜索结果</div>
                            ) : (
                                searchResults.map(msg => (
                                    <div key={msg.id} className="search-result-item" onClick={() => {
                                        setShowSearch(false);
                                        scrollToMessage(msg.id);
                                    }}>
                                        <div className="search-result-header">
                                            <span className="search-result-sender">{msg.nickname}</span>
                                            <div className="search-result-meta">
                                                <span className="search-result-time">{new Date(msg.timestamp).toLocaleString()}</span>
                                                {msg.id && (
                                                    <button
                                                        className="search-result-btn"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleDeleteMessage(msg.id as number);
                                                        }}
                                                    >
                                                        删除
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                        <div className="search-result-content">{msg.text}</div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Edit Message Modal */}
            {editingMessage && (
                <div className="edit-message-container">
                    <div className="edit-message-header">
                        <h3>编辑消息</h3>
                        <button className="edit-close-btn" onClick={() => setEditingMessage(null)}>×</button>
                    </div>
                    <div className="edit-message-input">
                        <textarea
                            className="edit-textarea"
                            defaultValue={editingMessage.text}
                            id="edit-message-textarea"
                        />
                    </div>
                    <div className="edit-message-actions">
                        <button className="edit-save-btn" onClick={() => {
                            const textarea = document.getElementById('edit-message-textarea') as HTMLTextAreaElement;
                            if (textarea && textarea.value.trim() && editingMessage.id) {
                                edit_message(editingMessage.id, textarea.value.trim());
                            }
                        }}>保存</button>
                        <button className="edit-cancel-btn" onClick={() => setEditingMessage(null)}>取消</button>
                    </div>
                </div>
            )}

            {/* Input */}
            <div className="input-container" style={{ height: `${inputHeight}px` }} ref={inputAreaRef}>
                <div
                    className="resize-handle"
                    onMouseDown={() => setIsResizing(true)}
                />
                {replyTo && (
                    <div className="reply-preview">
                        <div className="reply-preview-content">
                            <span className="reply-preview-label">回复</span>
                            <span className="reply-preview-sender">{replyTo.nickname}:</span>
                            {replyPreviewIsImage ? (
                                <span className="reply-preview-thumb">
                                    <img src={resolveMediaUrl(replyTo.text)} alt="reply image" />
                                </span>
                            ) : replyPreviewIsVideo && replyPreviewVideoThumb ? (
                                <span className="reply-preview-thumb video-thumb">
                                    <img src={replyPreviewVideoThumb} alt="reply video thumb" />
                                </span>
                            ) : (
                                <span className="reply-preview-text">{replyPreviewText}</span>
                            )}
                        </div>
                        <button onClick={() => setReplyTo(null)} className="reply-cancel">×</button>
                    </div>
                )}
                {/* 第一行：表情等选项 */}
                <div className="input-actions">
                    <button
                        title="表情"
                        onClick={() => setShowEmojiPanel(!showEmojiPanel)}
                        className="action-button emoji-button"
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                            <circle cx="12" cy="12" r="10" stroke="#666" strokeWidth="1.5"/>
                            <path d="M8 14s1.5 2 4 2 4-2 4-2" stroke="#666" strokeWidth="1.5" strokeLinecap="round"/>
                            <circle cx="9" cy="9" r="1" fill="#666"/>
                            <circle cx="15" cy="9" r="1" fill="#666"/>
                        </svg>
                    </button>
                    <label className="action-button file-button" title="上传文件/图片/音频/视频">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="#666" strokeWidth="1.5" strokeLinecap="round"/>
                            <path d="M17 8l-5-5-5 5" stroke="#666" strokeWidth="1.5" strokeLinecap="round"/>
                            <path d="M12 3v12" stroke="#666" strokeWidth="1.5" strokeLinecap="round"/>
                        </svg>
                        <input type="file" ref={fileInputRef} className="file-input" accept="image/*,audio/*,video/*" onChange={async (e) => {
                            const file = e.target.files?.[0]; if (!file) return;
                            if (!canSendCurrentConversation) {
                                toast.error(currentConv?.isGroup ? '你已不在该群聊，无法发送消息' : '当前会话不可用');
                                e.target.value = '';
                                return;
                            }
                            const maxSizeBytes = 50 * 1024 * 1024; // 50MB
                            if (file.size > maxSizeBytes) {
                                toast.error('文件过大，单个文件请小于 50MB');
                                e.target.value = '';
                                return;
                            }
                            try {
                                const form = new FormData(); form.append('file', file);
                                const token = localStorage.getItem('token');
                                const resp = await fetch(`https://${BACKEND_URL}/chat/upload`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form });
                                const data = await resp.json(); if (data.code !== 0) { console.error('上传失败', data.info); return; }
                                const url = data.url as string; if (!ws || ws.readyState !== WebSocket.OPEN) return;
                                let messageType: 'image' | 'audio' | 'video' | 'file' = 'file';
                                if (file.type.startsWith('image/')) messageType = 'image';
                                else if (file.type.startsWith('audio/')) messageType = 'audio';
                                else if (file.type.startsWith('video/')) messageType = 'video';
                                ws.send(JSON.stringify({ type: 'message', conversation: effectiveConvId, message: { type: messageType, content: url, reply_to: replyTo?.id } }));
                            } catch (err) { console.error('上传异常', err); } finally { if (fileInputRef.current) { fileInputRef.current.value = ''; } }
                        }} />
                    </label>
                </div>
                {/* 第二行：输入区域 */}
                <textarea
                    ref={textareaRef}
                    value={inputValue}
                    onChange={(e) => {
                        setInputValue(e.target.value);
                        // 自动调整文本框高度
                        if (textareaRef.current) {
                            textareaRef.current.style.height = 'auto';
                            const newHeight = Math.min(textareaRef.current.scrollHeight, inputHeight - 84); // 调整计算方式，考虑两行的高度
                            textareaRef.current.style.height = `${newHeight}px`;
                        }
                    }}
                    placeholder=" "
                    className="message-input"
                    onCompositionStart={() => setIsComposing(true)}
                    onCompositionEnd={() => setIsComposing(false)}
                    onKeyDown={(e) => {
                        const composing = isComposing || (e.nativeEvent as any).isComposing || e.keyCode === 229;
                        if (composing) return;
                        // 检测是否为换行组合键：Ctrl+Shift (Windows) 或 Cmd+Shift (Mac)
                        const isLineBreak = (e.key === "Enter" && (
                            (e.ctrlKey && e.shiftKey) ||
                            (e.metaKey && e.shiftKey)
                        ));
                        
                        // 普通Enter发送消息
                        if (e.key === "Enter" && !e.shiftKey && !isLineBreak) {
                            e.preventDefault();
                            send_message(inputValue);
                        }
                        
                        // 换行组合键允许默认行为（换行）
                        if (isLineBreak) {
                            // 不阻止默认行为，允许换行
                            return;
                        }
                    }}
                />
                <button
                    onClick={() => send_message(inputValue)}
                    className="send-button"
                    disabled={!inputValue.trim() || !canSendCurrentConversation}
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                        <path d="M22 2L11 13" stroke="white" strokeWidth="2" strokeLinecap="round"/>
                        <path d="M22 2l-7 20-4-9-9-4 20-7z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                </button>
                
                {/* 表情选择面板 */}
                {showEmojiPanel && (
                    <div className="emoji-panel">
                        <div className="emoji-panel-header">
                            <span>常用表情</span>
                            <button className="emoji-panel-close" onClick={() => setShowEmojiPanel(false)}>×</button>
                        </div>
                        <div className="emoji-grid">
                            {commonEmojis.map((emoji, index) => (
                                <button
                                    key={index}
                                    className="emoji-item"
                                    onClick={() => {
                                        setInputValue(v => `${v || ''}${emoji}`);
                                        setShowEmojiPanel(false);
                                        if (textareaRef.current) {
                                            textareaRef.current.focus();
                                        }
                                    }}
                                >
                                    {emoji}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
                
            </div>

            <style jsx>{`
                .chat-container {
                    width: 100%;
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(5px);
                    position: relative;
                    z-index: 1;
                }

                .empty-chat-container {
                    width: 100%;
                    height: 100%;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(5px);
                }

                .empty-chat-content {
                    text-align: center;
                    background: rgba(255, 255, 255, 0.8);
                    backdrop-filter: blur(10px);
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                    max-width: 400px;
                }

                .empty-chat-icon {
                    font-size: 64px;
                    margin-bottom: 20px;
                    display: block;
                }

                .empty-chat-title {
                    font-size: 24px;
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 8px;
                }

                .empty-chat-subtitle {
                    font-size: 16px;
                    color: #666;
                    line-height: 1.5;
                }

                .chat-header {
                    padding: 16px 20px;
                    background: rgba(255, 255, 255, 0.85);
                    backdrop-filter: blur(10px);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.3);
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
                }

                .chat-header-info {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }

                .chat-avatar {
                    width: 48px;
                    height: 48px;
                    border-radius: 12px;
                    overflow: hidden;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: grid;
                    place-items: center;
                    box-shadow: 0 4px 8px rgba(102, 126, 234, 0.2);
                }

                .chat-avatar-image {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }

                .chat-avatar-placeholder {
                    color: white;
                    font-weight: 700;
                    font-size: 18px;
                }

                .chat-header-details {
                    display: flex;
                    flex-direction: column;
                }

                .chat-title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #333;
                }

                .chat-status {
                    font-size: 13px;
                    color: #667eea;
                }

                .messages-container {
                    flex: 1;
                    overflow-y: auto;
                    padding: 20px;
                    background: transparent;
                }

                .messages-list {
                    max-width: 900px;
                    margin: 0 auto;
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }

                .message-wrapper {
                    display: flex;
                    justify-content: flex-start;
                }

                .message-wrapper.mine {
                    justify-content: flex-end;
                }

                .message-content {
                    display: flex;
                    align-items: flex-start;
                    gap: 8px;
                    max-width: 70%;
                }

                .message-avatar-container {
                    display: flex;
                    flex-direction: column-reverse;
                    align-items: center;
                    gap: 4px;
                }

                .message-avatar {
                    width: 36px;
                    height: 36px;
                    border-radius: 50%;
                    overflow: hidden;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    flex-shrink: 0;
                    border: 1px solid #000;
                }

                .sender-nickname {
                    font-size: 12px;
                    color: #333;
                    font-weight: 500;
                    max-width: 60px;
                    text-align: center;
                    word-break: break-all;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }

                .message-avatar-image {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }

                .message-bubble {
                    padding: 12px 16px;
                    border-radius: 18px;
                    word-break: break-word;
                    cursor: context-menu;
                    transition: all 0.2s ease;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                    max-width: 100%;
                }

                .message-bubble:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                }

                .message-bubble.theirs {
                    background: rgba(255, 255, 255, 0.95);
                    color: #333;
                    border-radius: 18px 18px 18px 6px;
                }

                .message-bubble.mine {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 18px 18px 6px 18px;
                }

                .message-reply {
                    font-size: 12px;
                    opacity: 0.8;
                    margin-bottom: 6px;
                    padding: 6px 10px;
                    background: rgba(0, 0, 0, 0.05);
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    border-left: 3px solid #667eea;
                }
                
                .message-reply:hover {
                    background: rgba(0, 0, 0, 0.1);
                    transform: translateX(2px);
                }
                
                /* 对于自己的消息（深色背景），回复内容的颜色调整为白色 */
                .message-bubble.mine .message-reply {
                    background: rgba(255, 255, 255, 0.15);
                    border-left-color: rgba(255, 255, 255, 0.5);
                }
                
                .message-bubble.mine .message-reply:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
                
                .reply-content {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }
                
                .reply-sender {
                    font-weight: 600;
                    color: #667eea;
                }
                
                /* 自己的消息中回复内容的颜色 */
                .message-bubble.mine .reply-sender {
                    color: rgba(255, 255, 255, 0.9);
                }
                
                .reply-text {
                    color: #666;
                    word-break: break-word;
                }

                .reply-thumb {
                    max-width: 160px;
                    max-height: 160px;
                    width: auto;
                    height: auto;
                    border-radius: 8px;
                    overflow: hidden;
                    background: #f5f5f5;
                    border: 1px solid rgba(0, 0, 0, 0.06);
                    flex-shrink: 0;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                }

                .reply-preview-thumb {
                    max-width: 96px;
                    max-height: 96px;
                    width: auto;
                    height: auto;
                    border-radius: 8px;
                    overflow: hidden;
                    background: #f5f5f5;
                    border: 1px solid rgba(0, 0, 0, 0.06);
                    flex-shrink: 0;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                }

                .reply-thumb.video-thumb,
                .reply-preview-thumb.video-thumb {
                    position: relative;
                }

                .reply-thumb.video-thumb::after,
                .reply-preview-thumb.video-thumb::after {
                    content: '视频';
                    position: absolute;
                    right: 6px;
                    bottom: 6px;
                    padding: 2px 6px;
                    background: rgba(0, 0, 0, 0.65);
                    color: #fff;
                    font-size: 12px;
                    border-radius: 4px;
                    line-height: 1.2;
                    pointer-events: none;
                }

                .reply-thumb img {
                    max-width: 160px;
                    max-height: 160px;
                    width: auto;
                    height: auto;
                    object-fit: contain;
                    display: block;
                }

                .reply-preview-thumb img {
                    max-width: 96px;
                    max-height: 96px;
                    width: auto;
                    height: auto;
                    object-fit: contain;
                    display: block;
                }

                .message-bubble.mine .reply-thumb {
                    border-color: rgba(255, 255, 255, 0.3);
                    background: rgba(255, 255, 255, 0.08);
                }
                
                /* 自己的消息中回复文本的颜色 */
                .message-bubble.mine .reply-text {
                    color: rgba(255, 255, 255, 0.8);
                }
                
                .reply-fallback {
                    color: #999;
                    font-style: italic;
                }
                
                /* 自己的消息中回复回退文本的颜色 */
                .message-bubble.mine .reply-fallback {
                    color: rgba(255, 255, 255, 0.7);
                }
                
                .reply-count {
                    font-weight: 600;
                    color: #667eea;
                    margin-left: 4px;
                    transition: color 0.2s ease;
                }
                
                /* 自己的消息中回复计数的颜色 */
                .message-bubble.mine .reply-count {
                    color: rgba(255, 255, 255, 0.9);
                }

                .message-image {
                    max-width: 260px;
                    border-radius: 8px;
                    display: block;
                    cursor: zoom-in;
                }

                .message-image-error {
                    padding: 8px 12px;
                    background: rgba(0, 0, 0, 0.05);
                    border-radius: 8px;
                    color: #666;
                    font-size: 14px;
                    text-align: center;
                    display: block;
                }
                
                .message-image-error.hidden {
                    display: none;
                }
                
                /* 确保自己的消息中图片错误提示是白色的 */
                .message-bubble.mine .message-image-error {
                    background: rgba(255, 255, 255, 0.1);
                    color: rgba(255, 255, 255, 0.8);
                }

                .message-file-link {
                    color: inherit;
                    text-decoration: underline;
                }

                .image-preview-backdrop {
                    position: fixed;
                    inset: 0;
                    background: rgba(0, 0, 0, 0.65);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 3000;
                    padding: 24px;
                    backdrop-filter: blur(2px);
                }

                .image-preview-body {
                    position: relative;
                    max-width: 90vw;
                    max-height: 90vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .image-preview-img {
                    max-width: 100%;
                    max-height: 100%;
                    border-radius: 12px;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
                    object-fit: contain;
                }

                .image-preview-close {
                    position: absolute;
                    top: -12px;
                    right: -12px;
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    border: none;
                    background: rgba(255, 255, 255, 0.9);
                    color: #333;
                    font-size: 18px;
                    cursor: pointer;
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.25);
                    display: grid;
                    place-items: center;
                }

                .image-preview-close:hover {
                    background: white;
                }
                
                /* 确保自己的消息中文件链接是白色的 */
                .message-bubble.mine .message-file-link {
                    color: white;
                }

                .input-container {
                    background: #f7f7f7;
                    border-top: 1px solid #e0e0e0;
                    position: relative;
                    min-height: 60px;
                    max-height: 300px;
                    resize: none;
                    display: flex;
                    flex-direction: column;
                }

                .input-actions {
                    display: flex;
                    gap: 8px;
                    padding: 8px 16px;
                    background: #f7f7f7;
                    border-bottom: 1px solid #e0e0e0;
                }

                .action-button {
                    width: 24px;
                    height: 24px;
                    border-radius: 4px;
                    border: none;
                    background: transparent;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .action-button:hover {
                    background: rgba(0, 0, 0, 0.05);
                }

                .action-button:active {
                    background: rgba(0, 0, 0, 0.1);
                }

                .emoji-button:hover svg,
                .file-button:hover svg {
                    stroke: #07c160;
                }

                .file-input {
                    display: none;
                }

                .reply-preview {
                    padding: 8px 16px;
                    border-left: 3px solid #07c160;
                    border-radius: 4px;
                    background: rgba(7, 193, 96, 0.1);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 14px;
                }
                
                .reply-preview-content {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    flex: 1;
                    overflow: hidden;
                }
                
                .reply-preview-label {
                    font-weight: 600;
                    color: #07c160;
                    white-space: nowrap;
                }
                
                .reply-preview-sender {
                    font-weight: 600;
                    color: #333;
                    white-space: nowrap;
                }
                
                .reply-preview-text {
                    color: #666;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }

                .reply-cancel {
                    background: none;
                    border: none;
                    font-size: 16px;
                    cursor: pointer;
                    color: #666;
                    margin-left: 8px;
                    padding: 0;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                }

                .reply-cancel:hover {
                    background: rgba(0, 0, 0, 0.1);
                }

                .message-input {
                    flex: 1;
                    border: none;
                    background: transparent;
                    padding: 12px 16px;
                    font-size: 16px;
                    line-height: 1.5;
                    resize: none;
                    outline: none;
                    min-height: 40px;
                    max-height: 120px;
                    overflow-y: auto;
                    width: calc(100% - 60px); /* 减去发送按钮的宽度 */
                }

                .send-button {
                    position: absolute;
                    right: 16px;
                    bottom: 12px;
                    width: 32px;
                    height: 32px;
                    border-radius: 4px;
                    background: #07c160;
                    color: white;
                    border: none;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.2s ease;
                    flex-shrink: 0;
                }

                .message-input::placeholder {
                    color: #999;
                }


                .send-button:hover {
                    background: #06ad56;
                }

                .send-button:active {
                    background: #059a4c;
                }

                .send-button:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                }

                .resize-handle {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 8px;
                    cursor: ns-resize;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 20;
                    transform: translateY(-50%);
                }

                .resize-handle::after {
                    content: '';
                    width: 40px;
                    height: 3px;
                    background: #ccc;
                    border-radius: 3px;
                    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
                }

                .resize-handle:hover::after {
                    background: #999;
                }
                .message-edited {
                    font-size: 12px;
                    color: #999;
                    margin-left: 4px;
                }
                
                /* 自己的消息中"已编辑"标记的颜色 */
                .message-bubble.mine .message-edited {
                    color: rgba(255, 255, 255, 0.7);
                }

                .message-menu {
                    position: fixed;
                    z-index: 2147483647;
                    background: #fff;
                    border: 1px solid rgba(15, 23, 42, 0.08);
                    border-radius: 999px;
                    box-shadow: 0 24px 60px rgba(15, 23, 42, 0.25);
                    padding: 6px 12px;
                    display: inline-flex;
                    gap: 8px;
                    align-items: center;
                    pointer-events: auto;
                }

                .message-menu::after {
                    content: '';
                    position: absolute;
                    width: 12px;
                    height: 12px;
                    background: #fff;
                    border-left: 1px solid rgba(15, 23, 42, 0.08);
                    border-top: 1px solid rgba(15, 23, 42, 0.08);
                    transform: rotate(45deg);
                    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.15);
                }

                .message-menu.below::after {
                    top: -6px;
                    left: 50%;
                    transform: translateX(-50%) rotate(45deg);
                }

                .message-menu.above::after {
                    bottom: -6px;
                    left: 50%;
                    transform: translateX(-50%) rotate(45deg);
                    border-left: none;
                    border-top: none;
                    border-right: 1px solid rgba(15, 23, 42, 0.08);
                    border-bottom: 1px solid rgba(15, 23, 42, 0.08);
                }

                .menu-item {
                    padding: 6px 14px;
                    cursor: pointer;
                    border-radius: 999px;
                    transition: background 0.2s ease, color 0.2s ease;
                    color: #0f172a;
                    font-size: 14px;
                    font-weight: 500;
                    white-space: nowrap;
                }

                .menu-item:hover {
                    background: rgba(102, 126, 234, 0.12);
                    color: #4c1d95;
                }

                .menu-item.editing {
                    color: #94a3b8;
                    cursor: default;
                    pointer-events: none;
                }

                .menu-item.danger {
                    color: #ef4444;
                }

                .menu-item.danger:hover {
                    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
                    color: #dc2626;
                }

                .edit-message-container {
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
                    z-index: 1001;
                    width: 90%;
                    max-width: 500px;
                }

                .edit-message-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 16px;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
                }

                .edit-close-btn {
                    background: none;
                    border: none;
                    font-size: 18px;
                    cursor: pointer;
                    color: #666;
                }

                .edit-message-input {
                    padding: 16px;
                }

                .edit-textarea {
                    width: 100%;
                    min-height: 100px;
                    border: 1px solid rgba(102, 126, 234, 0.2);
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 14px;
                    line-height: 1.5;
                    resize: vertical;
                    outline: none;
                }

                .edit-message-actions {
                    display: flex;
                    gap: 8px;
                    justify-content: flex-end;
                    padding: 0 16px 16px;
                }

                .edit-save-btn {
                    padding: 8px 16px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                }

                .edit-cancel-btn {
                    padding: 8px 16px;
                    background: #f0f0f0;
                    color: #333;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                }

                .system {
                    justify-content: center;
                }

                .system .message-content {
                    max-width: 100%;
                    justify-content: center;
                }

                .system .message-bubble,
                .message-bubble.system {
                    background: rgba(200, 200, 200, 0.5);
                    color: #888;
                    font-style: italic;
                    font-size: 13px;
                    border: none;
                    cursor: default;
                    border-radius: 12px;
                    padding: 8px 16px;
                    box-shadow: none;
                }

                .message-bubble.highlighted {
                    box-shadow: 0 0 0 8px rgba(102, 126, 234, 0.3);
                    transform: scale(1.02);
                    transition: all 0.3s ease;
                }

                .private-read-status {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: flex-end;
                    margin-bottom: 2px;
                }

                .private-read-status-indicator svg {
                    opacity: 0.7;
                    transition: opacity 0.2s ease;
                }

                .private-read-status-indicator:hover svg {
                    opacity: 1;
                }
                
                .message-status-container {
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: flex-end;
                    margin-bottom: 2px;
                    min-height: 24px; /* 确保容器有足够的高度 */
                    align-self: flex-end; /* 确保状态容器与消息底部对齐 */
                }
                
                .message-time-display {
                    position: absolute;
                    bottom: 100%;
                    right: 0;
                    font-size: 11px;
                    color: white;
                    white-space: nowrap;
                    opacity: 0.9;
                    transition: opacity 0.2s ease;
                    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
                    margin-bottom: 4px;
                    z-index: 10; /* 确保时间显示在其他元素之上 */
                    pointer-events: none; /* 防止时间显示干扰鼠标事件 */
                }
                
                /* 对于别人的消息，时间显示在消息气泡的右侧 */
                .message-bubble.theirs .message-time-display-others {
                    position: absolute;
                    top: 50%;
                    left: 100%;
                    transform: translateY(-50%);
                    font-size: 11px;
                    color: white;
                    white-space: nowrap;
                    opacity: 0.9;
                    transition: opacity 0.2s ease;
                    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
                    margin-left: 8px;
                    z-index: 10; /* 确保时间显示在其他元素之上 */
                    pointer-events: none; /* 防止时间显示干扰鼠标事件 */
                }
                
                .message-time-display:hover {
                    opacity: 1;
                }

                .emoji-panel {
                    position: absolute;
                    bottom: 100%;
                    left: 0;
                    width: 100%;
                    max-width: 400px;
                    background: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    z-index: 100;
                    margin-bottom: 8px;
                }

                .emoji-panel-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 16px;
                    border-bottom: 1px solid #f0f0f0;
                    font-size: 14px;
                    font-weight: 500;
                    color: #333;
                }

                .emoji-panel-close {
                    background: none;
                    border: none;
                    font-size: 18px;
                    cursor: pointer;
                    color: #999;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                }

                .emoji-panel-close:hover {
                    background: rgba(0, 0, 0, 0.05);
                }

                .emoji-grid {
                    display: grid;
                    grid-template-columns: repeat(8, 1fr);
                    gap: 4px;
                    padding: 8px;
                    max-height: 200px;
                    overflow-y: auto;
                }

                .emoji-item {
                    width: 36px;
                    height: 36px;
                    border: none;
                    background: transparent;
                    font-size: 20px;
                    cursor: pointer;
                    border-radius: 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: background 0.2s ease;
                }

                .emoji-item:hover {
                    background: rgba(0, 0, 0, 0.05);
                }

                .emoji-item:active {
                    background: rgba(0, 0, 0, 0.1);
                    transform: scale(0.95);
                }

                .search-result-meta {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .search-result-btn {
                    padding: 4px 8px;
                    border-radius: 6px;
                    border: 1px solid #fca5a5;
                    background: #fef2f2;
                    color: #b91c1c;
                    cursor: pointer;
                    font-size: 12px;
                    transition: all 0.2s ease;
                }

                .search-result-btn:hover {
                    background: #fee2e2;
                }

            `}</style>
        </div>
    );
}

function ReadReceipt({ total: _total, readBy, members, senderId }: { total: number, readBy: number[], members: Member[], senderId: number }) {
    // 排除发送者，只计算其他成员
    const otherMembers = members.filter(m => m.id !== senderId);
    const otherMembersCount = otherMembers.length;
    const readByOthers = readBy.filter(id => id !== senderId);
    const readCount = Math.min(readByOthers.length, otherMembersCount);
    const percent = otherMembersCount > 0 ? (readCount / otherMembersCount) : 0;
    const dash = `${percent * 100} ${100 - percent * 100}`;
    const [hover, setHover] = React.useState(false);
    const [_position, setPosition] = React.useState<'top' | 'bottom'>('bottom');
    const [tooltipStyle, setTooltipStyle] = React.useState<React.CSSProperties>({});
    const readReceiptRef = React.useRef<HTMLDivElement>(null);
    
    React.useEffect(() => {
        if (hover && readReceiptRef.current) {
            const rect = readReceiptRef.current.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            const _viewportWidth = window.innerWidth;
            const tooltipWidth = 220; // 预估的tooltip宽度
            
            // 动态计算tooltip高度（基于成员数量）
            const estimatedTooltipHeight = Math.min(50 + otherMembersCount * 24, 300);
            
            // 计算垂直位置
            let verticalPosition: 'top' | 'bottom' = 'bottom';
            let top: number | string, bottom: number | string;
            
            const spaceBelow = viewportHeight - rect.bottom;
            const spaceAbove = rect.top;
            
            if (spaceBelow >= estimatedTooltipHeight) {
                // 下方空间足够
                verticalPosition = 'bottom';
                top = rect.bottom + 10;
                bottom = 'auto';
            } else if (spaceAbove >= estimatedTooltipHeight) {
                // 上方空间足够
                verticalPosition = 'top';
                bottom = viewportHeight - rect.top + 10;
                top = 'auto';
            } else {
                // 两边都不够，选择空间更大的一边，并限制高度
                if (spaceBelow >= spaceAbove) {
                    verticalPosition = 'bottom';
                    top = rect.bottom + 10;
                    bottom = 'auto';
                } else {
                    verticalPosition = 'top';
                    bottom = viewportHeight - rect.top + 10;
                    top = 'auto';
                }
            }
            
            // 计算水平位置 - 始终显示在左边（因为自己的消息在右边）
            let left: number | string;
            
            // tooltip 显示在已读图标的左边
            const tooltipLeft = rect.left - tooltipWidth - 10;
            
            if (tooltipLeft >= 0) {
                // 左边有足够空间
                left = tooltipLeft;
            } else {
                // 左边空间不够，尽量靠左但不超出屏幕
                left = Math.max(10, tooltipLeft);
            }
            
            setPosition(verticalPosition);
            setTooltipStyle({ 
                top, 
                bottom, 
                left,
                right: 'auto',
                maxHeight: Math.max(spaceBelow, spaceAbove) - 20
            });
        }
    }, [hover, otherMembersCount]);
    
    const readNames = otherMembers.filter(m => readByOthers.includes(m.id)).map(m => m.nickname);
    const unreadNames = otherMembers.filter(m => !readByOthers.includes(m.id)).map(m => m.nickname);
    
    const tooltipContent = (
        <div className="read-receipt-tooltip" style={tooltipStyle}>
            <div className="read-receipt-title">已读 {readCount}/{otherMembersCount}</div>
            <div className="read-receipt-section">
                <div className="read-receipt-label">已读</div>
                <div className="read-receipt-names">
                    {readNames.length ? readNames.map(n => <span key={n} className="read-name">{n}</span>) : <span className="no-read-names">暂无</span>}
                </div>
            </div>
            <div className="read-receipt-section">
                <div className="read-receipt-label">未读</div>
                <div className="read-receipt-names">
                    {unreadNames.length ? unreadNames.map(n => <span key={n} className="unread-name">{n}</span>) : <span className="no-read-names">暂无</span>}
                </div>
            </div>
            <style jsx>{`
                .read-receipt-tooltip {
                    position: fixed;
                    background: white;
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                    padding: 12px;
                    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
                    z-index: 1000;
                    width: 220px;
                    max-width: 90vw;
                    overflow-y: auto;
                }

                .read-receipt-title {
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: #333;
                }

                .read-receipt-section {
                    margin-bottom: 8px;
                }

                .read-receipt-label {
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 4px;
                }

                .read-receipt-names {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 4px;
                }

                .read-name {
                    background: rgba(102, 126, 234, 0.1);
                    padding: 2px 6px;
                    border-radius: 6px;
                    font-size: 12px;
                }

                .unread-name {
                    background: rgba(0, 0, 0, 0.05);
                    padding: 2px 6px;
                    border-radius: 6px;
                    font-size: 12px;
                }

                .no-read-names {
                    color: #999;
                    font-size: 12px;
                }
            `}</style>
        </div>
    );

    return (
        <div className="read-receipt" ref={readReceiptRef} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
            <svg width="20" height="20" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="16" fill="#f0f0f0" />
                <circle cx="18" cy="18" r="16" fill="transparent" stroke="#667eea" strokeWidth="4" strokeDasharray={dash} transform="rotate(-90 18 18)" />
                <text x="18" y="21" textAnchor="middle" fontSize="12" fill="#333">{readCount}</text>
            </svg>
            {hover && typeof document !== 'undefined' && createPortal(tooltipContent, document.body)}
            <style jsx>{`
                .read-receipt {
                    position: relative;
                }
            `}</style>
        </div>
    );
}

function PrivateReadStatus({ isRead }: { isRead: boolean }) {
    return (
        <div className="private-read-status-indicator" title={isRead ? "已读" : "未读"}>
            {isRead ? (
                <div className="read-circle"></div>
            ) : (
                <div className="unread-circle"></div>
            )}
            <style jsx>{`
                .private-read-status-indicator {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-bottom: 4px;
                    width: 16px;
                    height: 16px;
                }
                
                .read-circle {
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
                    box-shadow: 0 1px 3px rgba(82, 196, 26, 0.3);
                }
                
                .unread-circle {
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    border: 2px solid #d9d9d9;
                    background: transparent;
                }
            `}</style>
        </div>
    );
}

function GroupMore({ convId, convName, convAvatar, membersCount, isGroup, onOpenSearch, onLoadFullHistory, loadingHistory, historyMessages }: { convId: number, convName?: string, convAvatar?: string, membersCount: number, isGroup?: boolean, onOpenSearch: () => void, onLoadFullHistory: () => void | Promise<void>, loadingHistory: boolean, historyMessages: Message[] }) {
    const [open, setOpen] = React.useState(false);
    const buttonRef = React.useRef<HTMLButtonElement>(null);

    const handleOpenSearch = () => {
        onOpenSearch();
        setOpen(false);
    };

    const handleLoadHistory = () => {
        onLoadFullHistory();
    };

    return (
        <>
            <div className="group-more">
                <button ref={buttonRef} onClick={() => setOpen(!open)} className="group-more-button">⋯</button>
            </div>
            {open && createPortal(
                <div className="group-more-overlay" onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
                    <div className="group-more-panel">
                        <div className="history-card">
                            <div className="history-card-header">
                                <div className="history-title">聊天记录</div>
                                <div className="history-subtitle">关键词搜索 · 按成员/时间筛选</div>
                            </div>
                            <div className="history-metadata">
                                <span className="history-meta-pill">{isGroup ? '群聊' : '会话'}</span>
                                {convName && <span className="history-name">{convName}</span>}
                                {isGroup && <span className="history-count">{membersCount} 人</span>}
                            </div>
                            <div className="history-actions">
                                <button className="history-btn primary" onClick={handleOpenSearch}>
                                    打开搜索/筛选
                                </button>
                                <button className="history-btn" onClick={handleLoadHistory} disabled={loadingHistory}>
                                    {loadingHistory ? '加载中...' : '加载全部历史'}
                                </button>
                            </div>
                            <div className="history-hint">支持关键词搜索、时间范围和成员筛选；删除记录只会在你这边隐藏。</div>
                            <div className="history-list">
                                {loadingHistory && historyMessages.length === 0 && <div className="history-empty">正在加载历史消息…</div>}
                                {!loadingHistory && historyMessages.length === 0 && <div className="history-empty">尚未加载历史消息</div>}
                                {historyMessages.map(msg => (
                                    <div key={msg.id ?? `${msg.sender}-${msg.timestamp}`} className="history-item">
                                        <div className="history-item-header">
                                            <span className="history-sender">{msg.nickname || msg.sender}</span>
                                            <span className="history-time">{msg.timestamp ? new Date(msg.timestamp).toLocaleString() : ''}</span>
                                            {msg.is_edited && <span className="history-edited">已编辑</span>}
                                        </div>
                                        {msg.reply_to_message && (
                                            <div className="history-reply">
                                                回复 → {msg.reply_to_message.nickname}: {msg.reply_to_message.text}
                                            </div>
                                        )}
                                        <div className="history-content">{msg.text}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        {isGroup && (
                            <div className="group-info-wrapper">
                                <GroupInfoPanel convId={convId} onClose={() => setOpen(false)} convName={convName} convAvatar={convAvatar} />
                            </div>
                        )}
                    </div>
                </div>,
                document.body
            )}
            <style jsx>{`
                .group-more {
                    position: relative;
                }

                .group-more-button {
                    width: 36px;
                    height: 36px;
                    border-radius: 8px;
                    border: 1px solid rgba(102, 126, 234, 0.2);
                    background: rgba(255, 255, 255, 0.8);
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .group-more-button:hover {
                    background: rgba(102, 126, 234, 0.1);
                }
                
                .group-more-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    z-index: 1000;
                    display: flex;
                    justify-content: flex-end;
                }
                
                .group-more-panel {
                    height: 100%;
                    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
                    display: flex;
                    gap: 12px;
                    align-items: stretch;
                    padding: 16px;
                    background: linear-gradient(120deg, rgba(102, 126, 234, 0.06) 0%, rgba(236, 233, 255, 0.6) 100%);
                }

                .history-card {
                    width: 320px;
                    background: #fff;
                    border-radius: 12px;
                    padding: 16px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }

                .history-card-header {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }

                .history-title {
                    font-size: 18px;
                    font-weight: 700;
                    color: #111827;
                }

                .history-subtitle {
                    font-size: 12px;
                    color: #6b7280;
                }

                .history-metadata {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    flex-wrap: wrap;
                }

                .history-meta-pill {
                    padding: 4px 10px;
                    background: rgba(102, 126, 234, 0.15);
                    color: #4c51bf;
                    border-radius: 999px;
                    font-size: 12px;
                    font-weight: 600;
                }

                .history-name {
                    font-size: 14px;
                    color: #374151;
                    font-weight: 600;
                }

                .history-count {
                    font-size: 12px;
                    color: #6b7280;
                }

                .history-actions {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                }

                .history-btn {
                    flex: 1;
                    min-width: 140px;
                    padding: 10px 12px;
                    border-radius: 10px;
                    border: 1px solid #dfe3f6;
                    background: #f9fafb;
                    color: #1f2937;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .history-btn:hover {
                    border-color: #a5b4fc;
                    background: #eef2ff;
                }

                .history-btn:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                    background: #f3f4f6;
                    border-color: #e5e7eb;
                }

                .history-btn.primary {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #fff;
                    border: none;
                    box-shadow: 0 10px 24px rgba(102, 126, 234, 0.25);
                }

                .history-btn.primary:hover {
                    transform: translateY(-1px);
                }

                .history-hint {
                    font-size: 12px;
                    color: #6b7280;
                    line-height: 1.6;
                }

                .history-list {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                    max-height: 360px;
                    overflow-y: auto;
                    padding-right: 4px;
                }

                .history-item {
                    border: 1px solid #e5e7eb;
                    border-radius: 10px;
                    padding: 10px 12px;
                    background: #f9fafb;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
                }

                .history-item-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 13px;
                    color: #374151;
                }

                .history-sender {
                    font-weight: 700;
                    color: #1f2937;
                }

                .history-time {
                    font-size: 12px;
                    color: #6b7280;
                }

                .history-edited {
                    font-size: 11px;
                    color: #ef4444;
                    padding: 2px 6px;
                    border-radius: 999px;
                    background: #fef2f2;
                    border: 1px solid #fecaca;
                }

                .history-reply {
                    margin-top: 6px;
                    padding: 6px 8px;
                    background: #eef2ff;
                    border-left: 3px solid #667eea;
                    border-radius: 8px;
                    color: #374151;
                    font-size: 13px;
                }

                .history-content {
                    margin-top: 6px;
                    font-size: 14px;
                    color: #111827;
                    line-height: 1.5;
                    word-break: break-word;
                }

                .history-empty {
                    font-size: 13px;
                    color: #6b7280;
                    padding: 8px;
                }

                .group-info-wrapper {
                    min-width: 360px;
                    height: 100%;
                }
            `}</style>
        </>
    );
}
"use client";

/**
 * 本程序向外提供Cotext接口：
 * 
 * - useUserContext()
 * - UserContextProvider()
 */

import {
    createContext,
    useContext,
    useState,
    useEffect,
    ReactNode,
    useRef,
    useCallback,
} from "react";
import { BACKEND_URL } from '../constant/strings'
import { toast } from "react-toastify";
import { Conversation, Message } from "@/types/Message";
import { User } from "@/types/User";
import { getPinnedConversations, pinConversation as pinConversationLocal, unpinConversation as unpinConversationLocal, isConversationPinned, getConversationPinOrder, savePinnedConversations } from "@/utils/pinStorage";

type RawMember = {
    id: number;
    nickname: string;
    avatar?: string;
    is_active?: boolean;
    is_online?: boolean;
    display_username?: string;
};

type RawMessage = {
    id: number;
    sender: number;
    sender_username?: string;
    content: string;
    type?: string;
    reply_to?: number;
    reply_to_message?: {
        id: number;
        sender: number;
        nickname: string;
        sender_nickname?: string;  // 群昵称
        text: string;
        type: string;
    };
    time: string;
    read_list?: number[];
    is_read?: boolean;
    valid?: boolean;  // 消息是否有效（撤回后为 false）
    sender_nickname?: string;  // 群昵称
};

type RawConversation = {
    id: number;
    name: string;
    type?: 'private' | 'group';
    is_group?: boolean;
    avatar?: string;
    members?: RawMember[];
    messages?: RawMessage[];
    unread_count?: number;
    pinned?: boolean;
    pin_order?: number;
    muted?: boolean;
};

const normalizeMediaUrl = (url?: string | null) => {
    if (!url) return '';
    if (/^https?:\/\//i.test(url)) return url;
    return `https://${BACKEND_URL}${url}`;
};

const convertHomeConversations = (list: RawConversation[]): Conversation[] => {
    const convs: Conversation[] = [];
    
    for (const conv of list) {
        const members = (conv.members ?? []).map((t) => {
            const displayName = t.nickname || t.display_username || '';
            return { 
                id: t.id, 
                nickname: displayName, 
                display_username: t.display_username,
                avatar: normalizeMediaUrl(t.avatar),
                is_active: t.is_active,
                is_online: t.is_online,
            };
        });
        const id2nick: Record<number, string> = {};
        members.forEach((m) => { id2nick[m.id] = m.nickname || m.display_username || ''; });
        const isGroup = conv.type === 'group' || conv.is_group === true;
        const isPrivateChat = !isGroup;
        
        const messages = (conv.messages ?? []).map((msg) => {
            // 如果消息已被撤回（valid === false），显示为系统消息
            const isRecalled = msg.valid === false;
            const senderDisplayName = msg.sender_nickname || msg.sender_username || id2nick[msg.sender];
            return {
                id: msg.id,
                sender: msg.sender,
                nickname: senderDisplayName ?? '',
                sender_nickname: msg.sender_nickname,  // 群昵称
                text: msg.content,
                type: isRecalled ? 'system' : (msg.type ?? 'text'),
                reply_to: msg.reply_to,
                reply_to_message: msg.reply_to_message,
                timestamp: new Date(msg.time),
                read_by: Array.isArray(msg.read_list) ? msg.read_list : undefined,
                is_read: isPrivateChat ? (msg.is_read ?? false) : undefined,  // 私聊消息确保有is_read字段
            };
        });
        
        // 优先使用后端返回的置顶状态和顺序；仅在后端未提供时才回退到本地缓存，避免伪置顶
        // 如果后端未返回pinned字段，则视为未置顶，避免本地缓存导致假置顶；后续同步接口会校准
        const isPinned = Boolean(conv.pinned);
        const pinOrder = typeof conv.pin_order === 'number' ? (conv.pin_order || getConversationPinOrder(conv.id)) : undefined;
        const isMuted = conv.muted || false;
        
        convs.push({
            id: conv.id,
            name: conv.name,
            avatar: normalizeMediaUrl(conv.avatar),
            messages,
            member: members,
            unread_count: conv.unread_count,
            isGroup,
            type: conv.type ?? (isGroup ? 'group' : 'private'),
            isPinned,
            pinOrder,
            isMuted
        });
    }
    return convs;
};

const fetchHomeConversations = async (tokenValue: string): Promise<Conversation[]> => {
    const homeResp = await fetch(`https://${BACKEND_URL}/new/home`, {
        method: "GET",
        headers: {
            Accept: "application/json",
            Authorization: "Bearer " + tokenValue,
        },
    });
    const homeData = await homeResp.json();
    const list = Array.isArray(homeData?.conversations) ? (homeData.conversations as RawConversation[]) : [];
    return convertHomeConversations(list);
};

interface UserContextType {
    login: (username: string, password: string) => Promise<{ success: boolean; needsRegister?: boolean; error?: string }>;
    register: (username: string, password: string) => Promise<boolean>;
    logout: () => void;
    token: string | null;
    username: string | null;
    setUsername: (name: string | null) => void;
    selfId: number | null;
    selfAvatar: string | null;
    setSelfAvatar: (url: string | null) => void;
    refreshSelfInfo: () => Promise<void>;
    refreshConversations: (options?: { silent?: boolean }) => Promise<void>;
    isLoading: boolean;
    isInitialized: boolean;

    conversations: Conversation[];
    update_message: (message: Message, conversation_id: number) => void;
    markConversationRead: (conversation_id: number) => void;
    ws: WebSocket | null;
    onlineUsers: Set<number>;
    isUserOnline: (id?: number | null) => boolean;

    // 映射信息
    id_to_username: Record<number, User>;
    update_id_to_username: (id: number, user: User) => void;
    
    // 置顶功能
    pinConversation: (conversationId: number) => Promise<boolean>;
    unpinConversation: (conversationId: number) => Promise<boolean>;
    syncPinnedConversations: () => Promise<void>;
    
    // 免打扰功能
    toggleMuteConversation: (conversationId: number, mute: boolean) => Promise<boolean>;

    // 历史记录功能
    searchHistory: (conversationId: number, query?: string, sender?: number, start?: string, end?: string) => Promise<Message[]>;
    deleteMessage: (messageId: number) => Promise<boolean>;
    mergeConversationMessages: (conversationId: number, messages: Message[]) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const useUserContext = () => {
    const context = useContext(UserContext);
    if (!context) {
        throw new Error("UserContext not found.");
    }
    return context;
};

export const logout = (setToken: (token: string|null) => void) => {
    setToken(null);
};

export const UserContextProvider = ({ children }: { children: ReactNode }) => {
    const [token, setToken] = useState<string|null>(null);
    const [username, setUsername] = useState<string|null>(null);
    const [selfId, setSelfId] = useState<number|null>(null);
    const [selfAvatar, setSelfAvatar] = useState<string|null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [isInitialized, setIsInitialized] = useState<boolean>(false);

    const wsRef = useRef<WebSocket | null>(null);
    const selfIdRef = useRef<number | null>(null);

    const [conversations, setConversations] = useState<Conversation[]>([]);
    const conversationsRef = useRef<Conversation[]>([]);
    // 用 state 存储以保证更新后可触发订阅组件重渲染
    const [id_to_username, setIdToUsername] = useState<Record<number, User>>({});
    const [onlineUsers, setOnlineUsers] = useState<Set<number>>(new Set());

    useEffect(() => {
        conversationsRef.current = conversations;
    }, [conversations]);

    useEffect(() => { selfIdRef.current = selfId; }, [selfId]);

    const setUserOnline = useCallback((userId: number, online: boolean) => {
        setOnlineUsers(prev => {
            const next = new Set(prev);
            if (online) {
                next.add(userId);
            } else {
                next.delete(userId);
            }
            return next;
        });
        setConversations(prev => prev.map(conv => ({
            ...conv,
            member: conv.member ? conv.member.map(m => m.id === userId ? { ...m, is_online: online } : m) : conv.member
        })));
    }, []);

    const isUserOnline = useCallback((id?: number | null) => {
        if (!id) return false;
        return onlineUsers.has(id);
    }, [onlineUsers]);

    const syncOnlineFromConversations = useCallback((convs: Conversation[]) => {
        const next = new Set<number>();
        convs.forEach(conv => {
            conv.member?.forEach(m => {
                if (m.is_online) next.add(m.id);
            });
        });
        setOnlineUsers(next);
    }, []);

    const logout = () => {
        setToken(null);
        setSelfAvatar(null);
        setUsername(null);
        setSelfId(null);
        setConversations([]);
        setOnlineUsers(new Set());
        selfIdRef.current = null;
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        localStorage.removeItem("token");
        localStorage.removeItem("username");
        localStorage.removeItem("user_id");
    };

    useEffect(() => {
        // 检查 localStorage 是否有登录状态
        const local_token = localStorage.getItem("token");
        const local_username = localStorage.getItem("username");
        const local_user_id = localStorage.getItem("user_id");
        if (local_token) {
            setToken(local_token);
            if (local_username) setUsername(local_username);
            if (local_user_id) setSelfId(Number(local_user_id));
        }
        // 标记初始化完成
        setIsInitialized(true);
    }, []);

    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, []);
    
    const update_message = useCallback((message: Message, conversation_id: number) => {
        setConversations(prev => {
            return prev.map(conv => {
                if (conv.id !== conversation_id) return conv;
                
                // 判断是否为私聊
                const isPrivateChat = conv.isGroup === false;
                
                // 检查消息是否已存在，如果存在则更新，否则添加
                const messageIndex = conv.messages.findIndex(m => m.id === message.id);
                let updatedMessages;
                let isNewMessage = false;
                
                if (messageIndex !== -1) {
                    // 消息已存在，更新它
                    updatedMessages = [...conv.messages];
                    updatedMessages[messageIndex] = { ...updatedMessages[messageIndex], ...message };
                } else {
                    // 新消息，添加它
                    updatedMessages = [...conv.messages, message];
                    isNewMessage = true;
                }
                
                // 如果是自己的消息，不需要增加未读计数
                const isOwnMessage = message.sender === selfId;
                
                // 计算未读消息数量
                let newUnreadCount;
                if (isPrivateChat) {
                    // 对于私聊，计算未读消息数量（不是自己发送的且未读的消息）
                    newUnreadCount = updatedMessages.filter(msg =>
                        msg.sender !== selfId && msg.is_read === false
                    ).length;
                } else {
                    // 对于群聊，保持原有逻辑
                    // 如果是新消息且不是自己发送的，增加未读计数
                    if (isNewMessage && !isOwnMessage) {
                        newUnreadCount = (conv.unread_count || 0) + 1;
                    } else {
                        newUnreadCount = conv.unread_count || 0;
                    }
                }
                
                return {
                    ...conv,
                    messages: updatedMessages,
                    unread_count: newUnreadCount
                };
            });
        });
    }, [selfId]);

    const refreshConversations = useCallback(async (options?: { silent?: boolean }) => {
        if (!token) return;
        const silent = Boolean(options?.silent);
        try {
            if (!silent) setIsLoading(true);
            const convs = await fetchHomeConversations(token);
            setConversations(convs);
            syncOnlineFromConversations(convs);
        } catch (e) {
            console.error('刷新会话失败', e);
        } finally {
            if (!silent) setIsLoading(false);
        }
    }, [token, syncOnlineFromConversations]);

    const handleWebsocketData = useCallback((raw: string) => {
        try {
            const data = JSON.parse(raw);
            if (data.type === "message") {
                const conversationId = Number(data.conversation);
                const payload = data.message;
                if (!conversationId || !payload) return;
                const conv = conversationsRef.current.find(c => c.id === conversationId);
                if (!conv) {
                    void refreshConversations({ silent: true });
                    return;
                }
                const senderIdRaw = payload.sender;
                const senderId = typeof senderIdRaw === 'number' ? senderIdRaw : Number(senderIdRaw ?? 0);
                const memberInfo = conv.member?.find(m => m.id === senderId);
                const nickname = (payload.sender_nickname || memberInfo?.nickname) ?? (senderId === selfId ? (username ?? "我") : `用户#${senderId || ''}`);
                
                // 判断是否为私聊
                const isPrivateChat = conv.isGroup === false;
                // 判断是否为接收方（不是发送者）
                const isReceiver = senderId !== selfId;
                
                const message: Message = {
                    id: payload.id,
                    sender: senderId,
                    text: payload.content,
                    type: payload.type ?? 'text',
                    nickname,
                    sender_nickname: payload.sender_nickname,  // 群昵称
                    timestamp: payload.time ? new Date(payload.time) : new Date(),
                    reply_to: payload.reply_to,
                    reply_to_message: payload.reply_to_message,
                    read_by: Array.isArray(payload.read_list) ? payload.read_list : undefined,
                    is_read: isPrivateChat && isReceiver ? false : undefined,  // 私聊接收方消息初始为未读，发送方消息初始状态也设为未读，等待已读回执
                };
                
                // 调试日志，检查消息类型
                if (payload.type === 'image') {
                }
                update_message(message, conversationId);
            } else if (data.type === "read_receipt_update") {
                const conversationId = Number(data.conversation);
                const messageId = Number(data.message_id);
                const userId = Number(data.user_id);
                
                if (!conversationId || !messageId || !userId) return;
                
                // 更新对应消息及之前所有消息的已读状态
                setConversations(prev => prev.map(conv => {
                    if (conv.id !== conversationId) return conv;
                    
                    // 判断是否为私聊
                    const isPrivateChat = conv.isGroup === false;
                    
                    const updatedMessages = conv.messages.map(msg => {
                        // 如果是当前消息或之后的消息，不处理
                        if (typeof msg.id === 'number' && msg.id > messageId) return msg;
                        
                        if (isPrivateChat) {
                            // 私聊：同步对方已读，记录在 read_by 里以便 UI 立刻展示
                            const currentReadBy = Array.isArray(msg.read_by) ? msg.read_by : [];
                            const newReadBy = currentReadBy.includes(userId) ? currentReadBy : [...currentReadBy, userId];
                            return {
                                ...msg,
                                is_read: true,
                                read_by: newReadBy
                            };
                        } else {
                            // 群聊：更新已读列表
                            const currentReadBy = Array.isArray(msg.read_by) ? msg.read_by : [];
                            const newReadBy = currentReadBy.includes(userId) ? currentReadBy : [...currentReadBy, userId];
                            
                            return {
                                ...msg,
                                read_by: newReadBy
                            };
                        }
                    });
                    
                    // 对于私聊，计算未读消息数量
                    let newUnreadCount = conv.unread_count;
                    if (isPrivateChat) {
                        // 计算未读消息数量（不是自己发送的且未读的消息）
                        newUnreadCount = updatedMessages.filter(msg =>
                            msg.sender !== selfId && msg.is_read === false
                        ).length;
                    }
                    
                    return {
                        ...conv,
                        messages: updatedMessages,
                        unread_count: newUnreadCount
                    };
                }));
            } else if (data.type === "read_receipt") {
                // 处理私聊已读回执
                const conversationId = Number(data.conversation);
                const messageId = Number(data.message_id);
                const readerId = Number(data.reader_id);
                
                if (!conversationId || !messageId || !readerId) return;
                
                setConversations(prev => prev.map(conv => {
                    if (conv.id !== conversationId) return conv;
                    
                    // 判断是否为私聊
                    const isPrivateChat = conv.isGroup === false;
                    
                    const updatedMessages = conv.messages.map(msg => {
                        if (msg.id !== messageId) return msg;
                        
                        if (isPrivateChat) {
                            // 私聊：同步对方已读，记录在 read_by 里以便 UI 立刻展示
                            const currentReadBy = Array.isArray(msg.read_by) ? msg.read_by : [];
                            const newReadBy = currentReadBy.includes(readerId) ? currentReadBy : [...currentReadBy, readerId];
                            return {
                                ...msg,
                                is_read: true,
                                read_by: newReadBy
                            };
                        } else {
                            // 群聊：更新已读列表
                            const currentReadBy = Array.isArray(msg.read_by) ? msg.read_by : [];
                            const newReadBy = currentReadBy.includes(readerId) ? currentReadBy : [...currentReadBy, readerId];
                            
                            return {
                                ...msg,
                                read_by: newReadBy
                            };
                        }
                    });
                    
                    // 对于私聊，计算未读消息数量
                    let newUnreadCount = conv.unread_count;
                    if (isPrivateChat) {
                        // 计算未读消息数量（不是自己发送的且未读的消息）
                        newUnreadCount = updatedMessages.filter(msg =>
                            msg.sender !== selfId && msg.is_read === false
                        ).length;
                    }
                    
                    return {
                        ...conv,
                        messages: updatedMessages,
                        unread_count: newUnreadCount
                    };
                }));
            } else if (data.type === "message_edited" || data.type === "edit_message") {
                const conversationId = Number(data.conversation);
                const messageId = Number(data.message_id);
                const content = data.content;
                const userId = Number(data.user_id);
                
                if (!conversationId || !messageId || content === undefined) return;
                
                // 更新对应消息的内容
                setConversations(prev => prev.map(conv => {
                    if (conv.id !== conversationId) return conv;
                    
                    const updatedMessages = conv.messages.map(msg => {
                        if (msg.id !== messageId) return msg;
                        
                        return {
                            ...msg,
                            text: content,
                            is_edited: true
                        };
                    });
                    
                    // 同时更新所有回复这条消息的回复消息的reply_to_message内容
                    const updatedMessagesWithReplies = updatedMessages.map(msg => {
                        if (msg.reply_to === messageId) {
                            return {
                                ...msg,
                                reply_to_message: {
                                    id: messageId,
                                    sender: userId,
                                    nickname: updatedMessages.find(m => m.id === messageId)?.sender_nickname || updatedMessages.find(m => m.id === messageId)?.nickname || '',
                                    text: content,
                                    type: 'text'
                                }
                            };
                        }
                        return msg;
                    });
                    
                    return {
                        ...conv,
                        messages: updatedMessagesWithReplies
                    };
                }));
            } else if (data.type === "message_recalled" || data.type === "recall_message") {
                const conversationId = Number(data.conversation);
                const messageId = Number(data.message_id);
                const userId = Number(data.user_id);
                
                if (!conversationId || !messageId) return;
                
                // 找到撤回消息的用户信息
                const conv = conversationsRef.current.find(c => c.id === conversationId);
                const memberInfo = conv?.member?.find(m => m.id === userId);
                const nickname = memberInfo?.nickname || `用户#${userId}`;
                
                // 创建撤回提示消息
                const recallMessage: Message = {
                    id: messageId,
                    sender: userId,
                    nickname,
                    sender_nickname: nickname,  // 群昵称
                    text: `${nickname}撤回了一条消息`,
                    type: 'system',
                    timestamp: new Date(),
                };
                
                // 将撤回的消息标记为无效，并添加撤回提示
                setConversations(prev => prev.map(conv => {
                    if (conv.id !== conversationId) return conv;
                    
                    const updatedMessages = conv.messages.map(msg => {
                        if (msg.id === messageId) {
                            // 返回撤回提示消息
                            return recallMessage;
                        }
                        return msg;
                    });
                    
                    // 同时更新所有回复这条消息的回复消息，将reply_to_message设为null
                    const updatedMessagesWithReplies = updatedMessages.map(msg => {
                        if (msg.reply_to === messageId) {
                            return {
                                ...msg,
                                reply_to: messageId,
                                reply_to_message: undefined
                            };
                        }
                        return msg;
                    });
                    
                    return {
                        ...conv,
                        messages: updatedMessagesWithReplies
                    };
                }));
            } else if (data.type === "conversation_event") {
                void refreshConversations({ silent: true });
            } else if (data.type === "presence") {
                const userId = Number(data.user_id);
                const online = data.status === 'online';
                if (userId) {
                    setUserOnline(userId, online);
                }
            } else if (data.type === "error") {
                // 处理WebSocket错误
                const errorType = data.error;
                const errorMessage = data.message || '未知错误';
                
                if (errorType === "not_friends") {
                    // 好友关系不存在，显示错误提示
                    toast.error(errorMessage);
                } else {
                    // 其他类型的错误
                    console.error("WebSocket错误:", errorType, errorMessage);
                    toast.error(errorMessage);
                }
            }
        } catch (err) {
        }
    }, [refreshConversations, selfId, update_message, username, setUserOnline]);

    const connectWebSocket = useCallback((tokenValue: string) => {
        if (!tokenValue) return;
        if (wsRef.current) wsRef.current.close();
        wsRef.current = new WebSocket(`wss://${BACKEND_URL}/ws/chat?token=${tokenValue}`);
        wsRef.current.onopen = () => {
            const me = selfIdRef.current;
            if (me) setUserOnline(me, true);
        };
        wsRef.current.onclose = () => {
            const me = selfIdRef.current;
            if (me) setUserOnline(me, false);
        };
        wsRef.current.onmessage = (event) => handleWebsocketData(event.data);
    }, [handleWebsocketData, setUserOnline]);

    const login = async (input_username: string, password: string): Promise<{ success: boolean; needsRegister?: boolean; error?: string }> => {
        try {
            const r = await fetch(`https://${BACKEND_URL}/account/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: input_username, password }),
            });

            const data = await r.json();

            if (data.code === 1003) {
                // 用户不存在，需要注册
                return { success: false, needsRegister: true };
            }

            if (data.code === 1004) {
                return { success: false, error: "密码错误" };
            }
            if (data.code !== 0) {
                return { success: false, error: `登录失败: ${data.info}` };
            }

            const tokenValue = data.jwt_token;
            setToken(tokenValue);
            setUsername(input_username);
            setSelfId(data.id ?? null);
            localStorage.setItem("token", tokenValue);
            localStorage.setItem("username", input_username);
            if (data.id) localStorage.setItem("user_id", String(data.id));

            setIsLoading(true);
            try {
                const convs = await fetchHomeConversations(tokenValue);
                setConversations(convs);
                syncOnlineFromConversations(convs);
            } finally {
                setIsLoading(false);
            }

            connectWebSocket(tokenValue);
            return { success: true };
        } catch (e) {
            console.error("登录失败", e);
            return { success: false, error: "网络错误，请稍后再试" };
        }
    };

    const register = async (input_username: string, password: string): Promise<boolean> => {
        try {
            const r = await fetch(`https://${BACKEND_URL}/account/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: input_username, password }),
            });

            const data = await r.json();
            
            if (data.code !== 0) {
                toast.error(`注册失败: ${data.info || '未知错误'}`);
                return false;
            }

            toast.success("注册成功！");
            return true;
        } catch (e) {
            console.error("注册失败", e);
            toast.error("注册失败，请稍后再试");
            return false;
        }
    };

    // 当 token 可用时（例如页面刷新后从 localStorage 恢复），自动拉取会话并建立 websocket
    useEffect(() => {
        if (!token) return;

        const loadHomeAndWs = async () => {
            try {
                setIsLoading(true);
                const convs = await fetchHomeConversations(token);
                setConversations(convs);
                syncOnlineFromConversations(convs);
                connectWebSocket(token);
            } catch (e) {
                console.error("恢复会话或建立 WebSocket 失败", e);
            } finally {
                setIsLoading(false);
            }
        };

        loadHomeAndWs();
    }, [token, connectWebSocket, syncOnlineFromConversations]);

    // 拉取本人信息（头像等）
    const refreshSelfInfo = useCallback(async () => {
        if (!token) return;
        try {
            const resp = await fetch(`https://${BACKEND_URL}/account/get_info`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const d = await resp.json();
            if (d && d.code === 0) {
                const ava: string = d.avatar || '';
                const norm = ava && ava.startsWith('/') ? `https://${BACKEND_URL}${ava}` : (ava || null);
                setSelfAvatar(norm);
            }
        } catch (e) {
            console.warn('refreshSelfInfo failed', e);
        }
    }, [token]);

    const mergeConversationMessages = useCallback((conversationId: number, messagesToMerge: Message[]) => {
        if (!messagesToMerge.length) return;
        setConversations(prev => prev.map(conv => {
            if (conv.id !== conversationId) return conv;

            // 使用 Map 去重，优先保留已有消息，再合并新消息
            const mergedMap = new Map<string | number, Message>();
            const buildKey = (msg: Message) => (typeof msg.id === 'number' ? msg.id : `${msg.sender}-${msg.timestamp?.valueOf?.() ?? 0}-${msg.text ?? ''}`);

            conv.messages.forEach(msg => mergedMap.set(buildKey(msg), msg));
            messagesToMerge.forEach(msg => {
                const key = buildKey(msg);
                const existing = mergedMap.get(key);
                // 如果已有记录，使用时间更新后的内容；否则直接插入
                mergedMap.set(key, existing ? { ...existing, ...msg } : msg);
            });

            const mergedList = Array.from(mergedMap.values()).sort((a, b) => {
                const at = a.timestamp ? a.timestamp.getTime() : 0;
                const bt = b.timestamp ? b.timestamp.getTime() : 0;
                return at - bt;
            });

            return { ...conv, messages: mergedList };
        }));
    }, []);

    // token 就绪时拉一次头像
    useEffect(() => { refreshSelfInfo(); }, [refreshSelfInfo]);

    const update_id_to_username = useCallback((id: number, user: User) => {
        setIdToUsername(prev => ({ ...prev, [id]: user }));
        setConversations(prev => prev.map(conv => {
            const updatedMembers = conv.member ? conv.member.map(m => m.id === id ? {
                ...m,
                nickname: user.name || m.nickname,
                display_username: user.name || m.display_username,
            } : m) : conv.member;

            if (conv.isGroup) return { ...conv, member: updatedMembers };

            const selfIdVal = selfIdRef.current;
            const otherMember = updatedMembers?.find(m => m.id !== selfIdVal);
            const shouldUpdateName = otherMember?.id === id;
            const nextName = shouldUpdateName ? (user.name || otherMember?.nickname || otherMember?.display_username || conv.name) : conv.name;

            return { ...conv, member: updatedMembers, name: nextName };
        }));
    }, []);

    const markConversationRead = useCallback((conversation_id: number) => {
        setConversations(prev => prev.map(c => {
            if (c.id !== conversation_id) return c;
            
            // 判断是否为私聊
            const isPrivateChat = c.isGroup === false;
            
            // 标记所有消息为已读
            const updatedMessages = c.messages.map(msg => {
                if (isPrivateChat) {
                    // 私聊：更新is_read字段
                    return { ...msg, is_read: true };
                } else {
                    // 群聊：保持原有逻辑
                    return msg;
                }
            });
            
            // 对于私聊，未读计数应该为0，因为所有消息都被标记为已读
            // 对于群聊，保持原有的unread_count逻辑
            return {
                ...c,
                unread_count: 0,
                messages: updatedMessages
            };
        }));
    }, []);

    // 置顶功能实现
    const pinConversationFunc = useCallback(async (conversationId: number): Promise<boolean> => {
        if (!token) return false;
        
        try {
            // 先调用API
            const response = await fetch(`https://${BACKEND_URL}/chat/pin`, {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ id: conversationId })
            });
            const data = await response.json();
            
            if (data.code === 0) {
                // API成功后，更新本地存储
                pinConversationLocal(conversationId);
                
                // 更新会话列表中的置顶状态
                setConversations(prev => prev.map(conv => {
                    if (conv.id === conversationId) {
                        const maxPinOrder = Math.max(...prev.filter(c => c.isPinned).map(c => c.pinOrder || 0), 0);
                        return {
                            ...conv,
                            isPinned: true,
                            pinOrder: maxPinOrder + 1
                        };
                    }
                    return conv;
                }));
                
                toast.success("会话已置顶");
                return true;
            } else {
                toast.error(data.info || "置顶失败");
                return false;
            }
        } catch (error) {
            console.error("置顶会话失败:", error);
            toast.error("置顶失败");
            return false;
        }
    }, [token]);

    const unpinConversationFunc = useCallback(async (conversationId: number): Promise<boolean> => {
        if (!token) return false;
        
        try {
            // 先调用API
            const response = await fetch(`https://${BACKEND_URL}/chat/unpin`, {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ id: conversationId })
            });
            const data = await response.json();
            
            if (data.code === 0) {
                // API成功后，更新本地存储
                unpinConversationLocal(conversationId);
                
                // 更新会话列表中的置顶状态
                setConversations(prev => {
                    const updated = prev.map(conv => {
                        if (conv.id === conversationId) {
                            return { ...conv, isPinned: false, pinOrder: undefined };
                        }
                        return conv;
                    });
                    
                    // 重新排序剩余置顶会话的pinOrder
                    const pinnedConvs = updated.filter(c => c.isPinned);
                    const sortedPinned = pinnedConvs.sort((a, b) => (a.pinOrder || 0) - (b.pinOrder || 0));
                    
                    return updated.map(conv => {
                        const pinnedIndex = sortedPinned.findIndex(p => p.id === conv.id);
                        if (conv.isPinned && pinnedIndex !== -1) {
                            return { ...conv, pinOrder: pinnedIndex + 1 };
                        }
                        return conv;
                    });
                });
                
                toast.success("已取消置顶");
                return true;
            } else {
                // 如果后端表示未置顶，清理本地伪置顶状态，避免界面卡住
                if (String(data.info || '').includes('not pinned') || data.code !== 0) {
                    unpinConversationLocal(conversationId);
                    setConversations(prev => prev.map(conv => conv.id === conversationId ? { ...conv, isPinned: false, pinOrder: undefined } : conv));
                }
                toast.error(data.info || "取消置顶失败");
                return false;
            }
        } catch (error) {
            console.error("取消置顶会话失败:", error);
            toast.error("取消置顶失败");
            return false;
        }
    }, [token]);

    // 免打扰功能实现
    const toggleMuteConversationFunc = useCallback(async (conversationId: number, mute: boolean): Promise<boolean> => {
        if (!token) return false;
        
        try {
            const response = await fetch(`https://${BACKEND_URL}/chat/member/set`, {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ id: conversationId, mute: mute })
            });
            const data = await response.json();
            
            if (data.code === 0) {
                setConversations(prev => prev.map(conv => {
                    if (conv.id === conversationId) {
                        return { ...conv, isMuted: mute };
                    }
                    return conv;
                }));
                toast.success(mute ? "已开启免打扰" : "已关闭免打扰");
                return true;
            } else {
                toast.error(data.info || "操作失败");
                return false;
            }
        } catch (error) {
            console.error("设置免打扰失败:", error);
            toast.error("设置失败");
            return false;
        }
    }, [token]);

    // 同步置顶状态
    const syncPinnedConversationsFunc = useCallback(async (): Promise<void> => {
        if (!token) return;
        
        try {
            // 获取服务器端的置顶会话列表
            const response = await fetch(`https://${BACKEND_URL}/chat/pinned`, {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                    "Authorization": `Bearer ${token}`
                }
            });
            const data = await response.json();
            
            if (data.code === 0 && Array.isArray(data.pinned)) {
                // 以服务器为唯一真相源，避免本地脏数据导致“假置顶”
                const serverPinned = data.pinned.map((id: number, index: number) => ({
                    id,
                    pinOrder: index + 1,
                    timestamp: Date.now()
                }));

                savePinnedConversations(serverPinned);

                setConversations(prev => prev.map(conv => {
                    const pinnedInfo = serverPinned.find((p: { id: number; pinOrder: number }) => p.id === conv.id);
                    if (pinnedInfo) {
                        return { ...conv, isPinned: true, pinOrder: pinnedInfo.pinOrder };
                    }
                    return { ...conv, isPinned: false, pinOrder: undefined };
                }));
            }
        } catch (error) {
            console.error("同步置顶状态失败:", error);
        }
    }, [token]);


    // 搜索历史记录
    const searchHistoryFunc = useCallback(async (conversationId: number, query?: string, sender?: number, start?: string, end?: string): Promise<Message[]> => {
        if (!token) {
            console.warn('searchHistory: no token, skip');
            return [];
        }
        try {
            const params = new URLSearchParams();
            params.append('c', conversationId.toString());
            if (query) params.append('q', query);
            if (sender) params.append('sender', sender.toString());
            if (start) params.append('start', start);
            if (end) params.append('end', end);

            const url = `https://${BACKEND_URL}/chat/history?${params.toString()}`;

            const response = await fetch(url, {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                    "Authorization": `Bearer ${token}`
                }
            });

            if (!response.ok) {
                console.error('[history] http error', response.status, response.statusText);
            }

            const data = await response.json();

            // 后端有时返回 { code, info, messages }，有时返回 { code, info, data: { messages } }
            const rawMessages = Array.isArray(data?.data?.messages)
                ? data.data.messages
                : (Array.isArray(data?.messages) ? data.messages : []);

            if (data.code === 0 && rawMessages.length) {
                return rawMessages.map((msg: any) => ({
                    id: msg.id,
                    sender: msg.sender_id,
                    nickname: msg.sender_nickname || msg.sender_username,
                    sender_nickname: msg.sender_nickname,  // 群昵称
                    sender_is_active: msg.sender_is_active,
                    text: msg.content,
                    type: msg.type,
                    reply_to: msg.reply_to,
                    reply_to_message: msg.reply_to_message,
                    timestamp: new Date(msg.time),
                    is_edited: msg.is_edited,
                    is_read: msg.is_read
                }));
            }

            console.warn('[history] non-zero code or empty messages', { code: data.code, info: data.info, messages: rawMessages?.length });
            return [];
        } catch (error) {
            console.error("搜索历史记录失败:", error);
            return [];
        }
    }, [token]);

    // 删除消息
    const deleteMessageFunc = useCallback(async (messageId: number): Promise<boolean> => {
        if (!token) return false;
        
        try {
            const response = await fetch(`https://${BACKEND_URL}/chat/message/delete`, {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ id: messageId })
            });
            const data = await response.json();
            
            if (data.code === 0) {
                // 更新本地会话中的消息列表
                setConversations(prev => prev.map(conv => {
                    // 检查该会话是否包含此消息
                    const hasMessage = conv.messages.some(m => m.id === messageId);
                    if (!hasMessage) return conv;
                    
                    // 移除消息
                    return {
                        ...conv,
                        messages: conv.messages.filter(m => m.id !== messageId)
                    };
                }));
                toast.success("删除成功");
                return true;
            } else {
                toast.error(data.info || "删除失败");
                return false;
            }
        } catch (error) {
            console.error("删除消息失败:", error);
            toast.error("删除失败");
            return false;
        }
    }, [token]);
    
    // token 就绪后主动同步一次置顶状态，避免界面显示本地陈旧置顶
    useEffect(() => {
        if (token) {
            void syncPinnedConversationsFunc();
        }
    }, [token, syncPinnedConversationsFunc]);


    return (
        <UserContext.Provider value={{
            login,
            register,
            logout,
            token,
            username,
            setUsername,
            selfId,
            selfAvatar,
            setSelfAvatar,
            refreshSelfInfo,
            refreshConversations,
            isLoading,
            isInitialized,
            onlineUsers,
            isUserOnline,
            conversations: conversations,
            update_message,
            markConversationRead,
            ws: wsRef.current,
            id_to_username,
            update_id_to_username,
            pinConversation: pinConversationFunc,
            unpinConversation: unpinConversationFunc,
            syncPinnedConversations: syncPinnedConversationsFunc,
            toggleMuteConversation: toggleMuteConversationFunc,
            searchHistory: searchHistoryFunc,
            deleteMessage: deleteMessageFunc,
            mergeConversationMessages
        }}>
            {children}
        </UserContext.Provider>
    );
};

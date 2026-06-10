import { BACKEND_URL } from "@/constant/strings";
import { Message } from "@/types/Message";
import { check_for_error, ApiResponse } from "./network";

interface ConversationIdResponse extends ApiResponse {
    id?: number;
}

interface HistoryMessageDto {
    id: number;
    sender: number;
    sender__username?: string;
    sender_username?: string;
    nickname?: string;
    sender_nickname?: string;
    content: string;
    timestamp: string;
}

interface HistoryResponse extends ApiResponse {
    messages?: HistoryMessageDto[];
}

export function get_conversation_id(token: string, to: number) {
    // 请求会话ID，不存在则创建
    return fetch(`https://${BACKEND_URL}/chat/create/friend`, {
        method: "POST",
        headers: {
            "Accept": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify({
            id: to
        })
    }).then(response => response.json() as Promise<ConversationIdResponse>)
    .then(data => {
        check_for_error(data);
        const conv_id = typeof data.id === "number" ? data.id : null;
        return conv_id;
    }).catch(err => {
        return null;
    })
}

export function get_history(token: string, conv_id: number): Promise<Message[]> {
    return fetch(`https://${BACKEND_URL}/message/history?c=${conv_id}`, {
        method: "GET",
        headers: {
            "Accept": "application/json",
            "Authorization": "Bearer " + token
        }
    }).then(response => response.json() as Promise<HistoryResponse>)
    .then(data => {
        check_for_error(data);
        const rawMessages = Array.isArray(data.messages) ? data.messages : [];
        const messages: Message[] = rawMessages.map((msg) => {
            const senderId = typeof msg.sender === "number" ? msg.sender : -1;
            const content = msg.content;
            const isImageUrl = typeof content === 'string' && /(\.png|\.jpg|\.jpeg|\.gif|\.webp)(\?.*)?$/i.test(content);
            const isAudioUrl = typeof content === 'string' && /(\.mp3|\.wav|\.m4a|\.aac|\.ogg)(\?.*)?$/i.test(content);
            const isVideoUrl = typeof content === 'string' && /(\.mp4|\.webm|\.mov|\.mkv|\.avi)(\?.*)?$/i.test(content);
            const derivedType: Message['type'] = isImageUrl ? 'image' : isAudioUrl ? 'audio' : isVideoUrl ? 'video' : 'text';
            return {
                id: msg.id,
                sender: senderId,
                nickname: msg.nickname ?? msg.sender_username ?? `用户#${senderId}`,
                sender_nickname: msg.sender_nickname, // 群昵称
                text: content,
                type: derivedType,
                timestamp: new Date(msg.timestamp), // 把字符串转成 Date 对象
            };
        });
        return messages;
    }).catch(err => {
        return [];
    })
}

export function connect_ws(conv_id: number, token: string) {
    const ws = new WebSocket(`wss://${BACKEND_URL}/ws/chat?c=${conv_id}&token=${token}`);
    return ws;
}

// 群管理相关 API
export interface GroupInfoResponse {
    id: number;
    name: string;
    avatar: string;
    role: 'owner' | 'admin' | 'member';
    announcement: string;
    members: Array<{
        id: number;
        nickname: string;
        avatar: string;
        role: string;
        is_active?: boolean;
    }>;
    isGroup: boolean; // 添加isGroup字段
}

export async function getGroupInfo(token: string, convId: number): Promise<GroupInfoResponse | null> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/group/info?id=${convId}`, {
            method: "GET",
            headers: {
                "Accept": "application/json",
                "Authorization": "Bearer " + token
            }
        });
        const data = await response.json();
        check_for_error(data);
        return {
            ...data,
            members: data.members || [],
            // 确保群聊信息中包含isGroup字段，设置为true
            isGroup: true
        };
    } catch (err) {
        return null;
    }
}

export async function updateGroupInfo(
    token: string,
    convId: number,
    name?: string,
    avatar?: string
): Promise<boolean> {
    try {
        const body: { id: number; name?: string; avatar?: string } = { id: convId };
        if (name !== undefined) body.name = name;
        if (avatar !== undefined) body.avatar = avatar;
        
        const response = await fetch(`https://${BACKEND_URL}/chat/group/update`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify(body)
        });
        const data = await response.json();
        check_for_error(data);
        return true;
    } catch (err) {
        return false;
    }
}

export async function setGroupAnnouncement(
    token: string,
    convId: number,
    content: string
): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/group/announce`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                id: convId,
                content: content
            })
        });
        const data = await response.json();
        check_for_error(data);
        return true;
    } catch (err) {
        return false;
    }
}

export async function getGroupAnnouncements(
    token: string,
    convId: number,
    limit?: number,
    offset?: number
): Promise<Array<{
    id: number;
    content: string;
    author_id: number | null;
    author_name: string;
    author_nickname?: string;
    created_at: string;
}>> {
    try {
        let url = `https://${BACKEND_URL}/chat/group/announcements?id=${convId}`;
        if (limit !== undefined) {
            url += `&limit=${limit}`;
        }
        if (offset !== undefined) {
            url += `&offset=${offset}`;
        }
        
        const response = await fetch(url, {
            method: "GET",
            headers: {
                "Accept": "application/json",
                "Authorization": "Bearer " + token
            }
        });
        const data = await response.json();
        check_for_error(data);
        return Array.isArray(data.announcements) ? data.announcements : [];
    } catch (err) {
        return [];
    }
}

export async function setMemberRole(
    token: string,
    convId: number,
    userId: number,
    role: 'admin' | 'member'
): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/group/role`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                id: convId,
                user_id: userId,
                role: role
            })
        });
        const data = await response.json();
        check_for_error(data);
        return true;
    } catch (err) {
        return false;
    }
}

export async function transferOwner(
    token: string,
    convId: number,
    toUserId: number
): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/group/transfer`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                id: convId,
                to: toUserId
            })
        });
        const data = await response.json();
        check_for_error(data);
        return true;
    } catch (err) {
        return false;
    }
}

export async function removeMember(
    token: string,
    convId: number,
    userId: number
): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/group/remove`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                id: convId,
                user_id: userId
            })
        });
        const data = await response.json();
        check_for_error(data);
        return true;
    } catch (err) {
        return false;
    }
}

export async function exitGroup(token: string, convId: number): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/group/exit`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                id: convId
            })
        });
        const data = await response.json();
        check_for_error(data);
        return true;
    } catch (err) {
        return false;
    }
}

export async function disbandGroup(token: string, convId: number): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/group/disband`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                id: convId
            })
        });
        const data = await response.json();
        check_for_error(data);
        return true;
    } catch (err) {
        return false;
    }
}

export async function setGroupNickname(
    token: string,
    convId: number,
    nickname: string
): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/group/nickname`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                id: convId,
                nickname: nickname
            })
        });
        const data = await response.json();
        check_for_error(data);
        return true;
    } catch (err) {
        return false;
    }
}

// 置顶相关 API
export async function pinConversation(token: string, convId: number): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/pin`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                id: convId
            })
        });
        const data = await response.json();
        check_for_error(data);
        return true;
    } catch (err) {
        return false;
    }
}

export async function unpinConversation(token: string, convId: number): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/unpin`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                id: convId
            })
        });
        const data = await response.json();
        check_for_error(data);
        return true;
    } catch (err) {
        return false;
    }
}

export async function getPinnedConversations(token: string): Promise<number[]> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/pinned`, {
            method: "GET",
            headers: {
                "Accept": "application/json",
                "Authorization": "Bearer " + token
            }
        });
        const data = await response.json();
        check_for_error(data);
        return Array.isArray(data.pinned) ? data.pinned : [];
    } catch (err) {
        return [];
    }
}

// 群聊邀请相关 API
export interface GroupInvitation {
    id: number;
    inviter_id: number;
    inviter_name: string;
    inviter_nickname?: string;
    invitee_id: number;
    invitee_name: string;
    invitee_nickname?: string;
    status: 'pending' | 'approved' | 'rejected' | 'expired';
    created_at: string;
    message: string;
    reviewer_id?: number;
    reviewer_name?: string;
    reviewer_nickname?: string;
    review_time?: string;
    review_comment?: string;
}

export interface UserInvitation {
    id: number;
    group_id: number;
    group_name: string;
    inviter_id: number;
    inviter_name: string;
    status: 'pending' | 'approved' | 'rejected' | 'expired';
    created_at: string;
    message: string;
}

// 邀请好友加入群聊
export async function inviteToGroup(
    token: string,
    groupId: number,
    friendId: number,
    message?: string
): Promise<{ success: boolean, invitationId?: number, error?: string }> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/group/invite`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                group_id: groupId,
                friend_id: friendId,
                message: message || ''
            })
        });
        const data = await response.json();
        if (data.code === 0) {
            return {
                success: true,
                invitationId: data.id
            };
        } else {
            return {
                success: false,
                error: data.info || '邀请失败'
            };
        }
    } catch (err) {
        return {
            success: false,
            error: '网络错误，请重试'
        };
    }
}

// 获取群聊的邀请列表（群主和管理员）
export async function getGroupInvitations(
    token: string,
    groupId: number,
    status?: 'pending' | 'approved' | 'rejected' | 'expired'
): Promise<GroupInvitation[]> {
    try {
        let url = `https://${BACKEND_URL}/chat/group/invitations?group_id=${groupId}`;
        if (status) {
            url += `&status=${status}`;
        }
        
        const response = await fetch(url, {
            method: "GET",
            headers: {
                "Accept": "application/json",
                "Authorization": "Bearer " + token
            }
        });
        const data = await response.json();
        if (data.code === 0) {
            return Array.isArray(data.invitations) ? data.invitations : [];
        } else {
            console.error("获取群聊邀请列表失败:", data.info);
            return [];
        }
    } catch (err) {
        return [];
    }
}

// 审核群聊邀请（群主和管理员）
export async function reviewGroupInvitation(
    token: string,
    invitationId: number,
    action: 'approve' | 'reject',
    comment?: string
): Promise<{ success: boolean, error?: string }> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/chat/group/invitation/review`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                invitation_id: invitationId,
                action: action,
                comment: comment || ''
            })
        });
        const data = await response.json();
        if (data.code === 0) {
            return { success: true };
        } else {
            return {
                success: false,
                error: data.info || '审核失败'
            };
        }
    } catch (err) {
        return {
            success: false,
            error: '网络错误，请重试'
        };
    }
}

// 获取用户收到的群聊邀请列表
export async function getUserInvitations(
    token: string,
    status?: 'pending' | 'approved' | 'rejected' | 'expired'
): Promise<UserInvitation[]> {
    try {
        let url = `https://${BACKEND_URL}/chat/user/invitations`;
        if (status) {
            url += `?status=${status}`;
        }
        
        const response = await fetch(url, {
            method: "GET",
            headers: {
                "Accept": "application/json",
                "Authorization": "Bearer " + token
            }
        });
        const data = await response.json();
        if (data.code === 0) {
            return Array.isArray(data.invitations) ? data.invitations : [];
        } else {
            console.error("获取用户邀请列表失败:", data.info);
            return [];
        }
    } catch (err) {
        return [];
    }
}
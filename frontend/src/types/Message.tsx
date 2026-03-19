import { Member } from './User'


export type Message = {
    id?: number;
    text?: string;
    type?: string; // 'text' | 'image' | 'file' | 'emoji' ...
    reply_to?: number;
    reply_to_message?: {
        id: number;
        sender: number;
        nickname: string;
        sender_nickname?: string; // 群昵称
        text: string;
        type: string;
    };
    sender: number;
    nickname: string;
    sender_nickname?: string; // 群昵称
    sender_is_active?: boolean;
    timestamp: Date;
    url?: string;
    read_by?: number[]; // 已读的用户id列表（群聊展示）
    is_read?: boolean; // 当前用户是否已读此消息
    is_edited?: boolean; // 消息是否已被编辑
};

export type Conversation = {
    id: number,  // conv_id
    name: string,
    type?: 'private' | 'group',
    avatar?: string,
    member: Member[],
    messages: Message[],
    unread_count?: number,
    isGroup?: boolean, // 添加字段标识是否为群聊
    isPinned?: boolean, // 添加字段标识是否置顶
    pinOrder?: number, // 添加字段表示置顶顺序，用于多个置顶会话的排序
    isMuted?: boolean, // 添加字段标识是否免打扰
}

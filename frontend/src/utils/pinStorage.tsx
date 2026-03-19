// 置顶会话本地存储工具

const PINNED_CONVERSATIONS_KEY = 'pinned_conversations';
const PINNED_CONVERSATIONS_ORDER_KEY = 'pinned_conversations_order';

export interface PinnedConversation {
    id: number;
    pinOrder: number;
    timestamp: number; // 添加时间戳，用于排序
}

// 获取置顶会话列表
export function getPinnedConversations(): PinnedConversation[] {
    if (typeof window === 'undefined') return [];
    
    try {
        const pinned = localStorage.getItem(PINNED_CONVERSATIONS_KEY);
        return pinned ? JSON.parse(pinned) : [];
    } catch (error) {
        console.error('获取置顶会话列表失败:', error);
        return [];
    }
}

// 保存置顶会话列表
export function savePinnedConversations(pinnedConversations: PinnedConversation[]): void {
    if (typeof window === 'undefined') return;
    
    try {
        localStorage.setItem(PINNED_CONVERSATIONS_KEY, JSON.stringify(pinnedConversations));
    } catch (error) {
        console.error('保存置顶会话列表失败:', error);
    }
}

// 置顶会话
export function pinConversation(convId: number): PinnedConversation[] {
    const pinned = getPinnedConversations();
    
    // 检查是否已经置顶
    const existingIndex = pinned.findIndex(p => p.id === convId);
    if (existingIndex !== -1) {
        // 如果已经置顶，不重复操作
        return pinned;
    }
    
    // 获取最大的pinOrder
    const maxPinOrder = pinned.length > 0 ? Math.max(...pinned.map(p => p.pinOrder)) : 0;
    
    // 添加新的置顶会话
    const newPinned: PinnedConversation = {
        id: convId,
        pinOrder: maxPinOrder + 1,
        timestamp: Date.now()
    };
    
    const updatedPinned = [...pinned, newPinned];
    savePinnedConversations(updatedPinned);
    return updatedPinned;
}

// 取消置顶会话
export function unpinConversation(convId: number): PinnedConversation[] {
    const pinned = getPinnedConversations();
    
    // 过滤掉取消置顶的会话
    const updatedPinned = pinned.filter(p => p.id !== convId);
    
    // 重新排序pinOrder，确保连续
    const reorderedPinned = updatedPinned
        .sort((a, b) => a.pinOrder - b.pinOrder)
        .map((p, index) => ({ ...p, pinOrder: index + 1 }));
    
    savePinnedConversations(reorderedPinned);
    return reorderedPinned;
}

// 检查会话是否已置顶
export function isConversationPinned(convId: number): boolean {
    const pinned = getPinnedConversations();
    return pinned.some(p => p.id === convId);
}

// 获取会话的置顶顺序
export function getConversationPinOrder(convId: number): number {
    const pinned = getPinnedConversations();
    const pinnedConv = pinned.find(p => p.id === convId);
    return pinnedConv ? pinnedConv.pinOrder : 0;
}

// 清空所有置顶会话
export function clearAllPinnedConversations(): void {
    if (typeof window === 'undefined') return;
    
    try {
        localStorage.removeItem(PINNED_CONVERSATIONS_KEY);
        localStorage.removeItem(PINNED_CONVERSATIONS_ORDER_KEY);
    } catch (error) {
        console.error('清空置顶会话列表失败:', error);
    }
}
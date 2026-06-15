"use client";

import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useUserContext } from '@/context/UserContext';
import { inviteToGroup } from '@/utils/message';
import { get_friends_api, get_friend_info } from '@/utils/friend';
import Avatar from './Avatar';

interface Friend {
    id: number;
    name: string;
    avatar: string;
    info: string;
    isAlreadyInGroup?: boolean; // 添加标记，表示是否已在群内
}

interface InviteFriendModalProps {
    isOpen: boolean;
    onClose: () => void;
    groupId: number;
    groupName: string;
    groupMembers?: number[]; // 添加群成员ID列表
}

export default function InviteFriendModal({ isOpen, onClose, groupId, groupName, groupMembers = [] }: InviteFriendModalProps) {
    const { token } = useUserContext();
    const [friends, setFriends] = useState<Friend[]>([]);
    const [loading, setLoading] = useState(true);
    const [inviting, setInviting] = useState<number | null>(null);
    const [inviteMessage, setInviteMessage] = useState('');
    const [selectedFriend, setSelectedFriend] = useState<Friend | null>(null);
    const [filterText, setFilterText] = useState('');

    // 加载好友列表
    useEffect(() => {
        if (!isOpen || !token) return;

        const loadFriends = async () => {
            setLoading(true);
            try {
                const [friendIds] = await get_friends_api(token);
                const friendDetails: Friend[] = [];
                
                for (const id of friendIds) {
                    const friendInfo = await get_friend_info(token, id);
                    // 检查好友是否已经在群内
                    const isAlreadyInGroup = groupMembers.includes(id);
                    friendDetails.push({
                        ...friendInfo,
                        avatar: friendInfo.avatar || '',
                        info: friendInfo.info || '',
                        isAlreadyInGroup
                    });
                }
                
                setFriends(friendDetails);
            } catch (error) {
                console.error('加载好友列表失败:', error);
                toast.error('加载好友列表失败');
            } finally {
                setLoading(false);
            }
        };

        loadFriends();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, token]);

    // 过滤好友列表
    const filteredFriends = friends.filter(friend => 
        friend.name.toLowerCase().includes(filterText.toLowerCase())
    );

    // 邀请好友
    const handleInviteFriend = async () => {
        if (!selectedFriend || !token) return;

        // 检查好友是否已经在群内
        if (selectedFriend.isAlreadyInGroup) {
            toast.error(`${selectedFriend.name} 已经在群聊中`);
            return;
        }

        setInviting(selectedFriend.id);
        try {
            const result = await inviteToGroup(
                token,
                groupId,
                selectedFriend.id,
                inviteMessage
            );
            
            if (result.success) {
                toast.success(`已邀请 ${selectedFriend.name} 加入群聊`);
                setSelectedFriend(null);
                setInviteMessage('');
                onClose();
            } else {
                toast.error(result.error || '邀请失败');
            }
        } catch (error) {
            console.error('邀请好友失败:', error);
            toast.error('邀请失败，请重试');
        } finally {
            setInviting(null);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1500
        }}>
            <div style={{
                backgroundColor: 'white',
                borderRadius: 12,
                width: '90%',
                maxWidth: 500,
                maxHeight: '80%',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
            }}>
                {/* 标题栏 */}
                <div style={{
                    padding: 16,
                    borderBottom: '1px solid #eee',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                }}>
                    <div style={{ fontSize: 16, fontWeight: 600 }}>
                        邀请好友加入「{groupName}」
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            border: 'none',
                            background: 'transparent',
                            cursor: 'pointer',
                            fontSize: 18,
                            color: '#666'
                        }}
                    >
                        ×
                    </button>
                </div>
                
                {/* 搜索框 */}
                <div style={{ padding: 16, borderBottom: '1px solid #f0f0f0' }}>
                    <input
                        type="text"
                        placeholder="搜索好友"
                        value={filterText}
                        onChange={(e) => setFilterText(e.target.value)}
                        style={{
                            width: '100%',
                            padding: '10px 12px',
                            border: '1px solid #e0e0e0',
                            borderRadius: 8,
                            outline: 'none',
                            fontSize: 14
                        }}
                    />
                </div>
                
                {/* 好友列表 */}
                <div style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: 16
                }}>
                    {loading ? (
                        <div style={{ textAlign: 'center', padding: 20 }}>加载中...</div>
                    ) : filteredFriends.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                            {filterText ? '没有找到匹配的好友' : '暂无可邀请的好友'}
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {filteredFriends.map((friend) => (
                                <div
                                    key={friend.id}
                                    onClick={() => !friend.isAlreadyInGroup && setSelectedFriend(friend)}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 12,
                                        padding: 12,
                                        borderRadius: 8,
                                        cursor: friend.isAlreadyInGroup ? 'not-allowed' : 'pointer',
                                        border: selectedFriend?.id === friend.id
                                            ? '2px solid #007aff'
                                            : '1px solid #f0f0f0',
                                        backgroundColor: selectedFriend?.id === friend.id
                                            ? '#f0f8ff'
                                            : (friend.isAlreadyInGroup ? '#f5f5f5' : 'white'),
                                        opacity: friend.isAlreadyInGroup ? 0.6 : 1
                                    }}
                                >
                                    <Avatar
                                        src={friend.avatar}
                                        size={40}
                                        alt={friend.name}
                                        fallbackText={friend.name?.charAt(0)}
                                    />
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontWeight: 500, fontSize: 14 }}>
                                            {friend.name}
                                            {friend.isAlreadyInGroup && (
                                                <span style={{
                                                    marginLeft: 8,
                                                    fontSize: 12,
                                                    color: '#999',
                                                    background: '#f0f0f0',
                                                    padding: '2px 6px',
                                                    borderRadius: 4
                                                }}>
                                                    已在群内
                                                </span>
                                            )}
                                        </div>
                                        {friend.info && (
                                            <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
                                                {friend.info}
                                            </div>
                                        )}
                                    </div>
                                    {selectedFriend?.id === friend.id && (
                                        <div style={{
                                            width: 20,
                                            height: 20,
                                            borderRadius: '50%',
                                            backgroundColor: '#007aff',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            color: 'white',
                                            fontSize: 12
                                        }}>
                                            ✓
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
                
                {/* 邀请附言 */}
                {selectedFriend && (
                    <div style={{ padding: 16, borderTop: '1px solid #f0f0f0' }}>
                        <textarea
                            placeholder="添加邀请附言（可选）"
                            value={inviteMessage}
                            onChange={(e) => setInviteMessage(e.target.value)}
                            style={{
                                width: '100%',
                                minHeight: 60,
                                padding: '10px 12px',
                                border: '1px solid #e0e0e0',
                                borderRadius: 8,
                                outline: 'none',
                                resize: 'vertical',
                                fontSize: 14
                            }}
                        />
                    </div>
                )}
                
                {/* 底部按钮 */}
                <div style={{
                    padding: 16,
                    borderTop: '1px solid #eee',
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: 12
                }}>
                    <button
                        onClick={onClose}
                        style={{
                            padding: '8px 16px',
                            border: '1px solid #e0e0e0',
                            borderRadius: 8,
                            background: 'white',
                            cursor: 'pointer',
                            fontSize: 14
                        }}
                    >
                        取消
                    </button>
                    <button
                        onClick={handleInviteFriend}
                        disabled={!selectedFriend || inviting === selectedFriend.id}
                        style={{
                            padding: '8px 16px',
                            border: 'none',
                            borderRadius: 8,
                            background: selectedFriend 
                                ? (inviting === selectedFriend.id ? '#ccc' : '#007aff') 
                                : '#ccc',
                            color: 'white',
                            cursor: selectedFriend 
                                ? (inviting === selectedFriend.id ? 'not-allowed' : 'pointer') 
                                : 'not-allowed',
                            fontSize: 14
                        }}
                    >
                        {selectedFriend ? (inviting === selectedFriend.id ? '邀请中...' : '邀请') : '邀请'}
                    </button>
                </div>
            </div>
        </div>
    );
}
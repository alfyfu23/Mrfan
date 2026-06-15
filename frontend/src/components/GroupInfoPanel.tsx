"use client";

import React, { useCallback, useEffect, useState, useRef } from 'react';
import { toast } from 'react-toastify';
import { BACKEND_URL } from '@/constant/strings';
import { useUserContext } from '@/context/UserContext';
import { updateGroupInfo, setMemberRole, transferOwner, removeMember, exitGroup, disbandGroup, getGroupInfo, getGroupAnnouncements, GroupInfoResponse } from '@/utils/message';
import { checkFriendship, sendFriendRequest } from '@/utils/friend';
import InviteFriendModal from './InviteFriendModal';
import GroupInvitationsPanel from './GroupInvitationsPanel';

export default function GroupInfoPanel({ convId, onClose, convName: _convName, convAvatar: _convAvatar }: { convId: number, onClose: ()=>void, convName?: string, convAvatar?: string }) {
    const { token, selfId, refreshConversations } = useUserContext();
    const [loading, setLoading] = useState(true);
    const [groupInfo, setGroupInfo] = useState<GroupInfoResponse | null>(null);
    const [editingName, setEditingName] = useState(false);
    const [newName, setNewName] = useState('');
    const [editingAvatar, setEditingAvatar] = useState(false);
    const [newAvatar, setNewAvatar] = useState('');
    const [announcement, setAnnouncement] = useState('');
    const [showHistoryAnnouncements, setShowHistoryAnnouncements] = useState(false);
    const [historyAnnouncements, setHistoryAnnouncements] = useState<Array<{
        id: number;
        content: string;
        author_id: number | null;
        author_name: string;
        author_nickname?: string;
        created_at: string;
    }>>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const fileRef = useRef<HTMLInputElement | null>(null);
    
    // 编辑群昵称相关状态
    const [editingNickname, setEditingNickname] = useState(false);
    const [newNickname, setNewNickname] = useState('');
    
    // 邀请相关状态
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [showInvitationsPanel, setShowInvitationsPanel] = useState(false);
    
    // 好友关系状态
    const [friendshipStatus, setFriendshipStatus] = useState<Record<number, boolean>>({});
    const [checkingFriendship, setCheckingFriendship] = useState<Record<number, boolean>>({});

    const load = useCallback(async () => {
        if (!token) return;
        try {
            const info = await getGroupInfo(token, convId);
            if (info) {
                setGroupInfo(info);
                setNewName(info.name);
                setNewAvatar(info.avatar);
                setAnnouncement(info.announcement);
            }
        } finally { setLoading(false); }
    }, [token, convId]);

    useEffect(() => { load(); }, [load]);

    const handleSaveName = async () => {
        if (!token || !groupInfo) return;
        const success = await updateGroupInfo(token, convId, newName);
        if (success) {
            toast.success('群名称修改成功');
            setEditingName(false);
            load();
        } else {
            toast.error('群名称修改失败');
        }
    };

    const handleSaveAvatar = async () => {
        if (!token || !groupInfo) return;
        const success = await updateGroupInfo(token, convId, undefined, newAvatar);
        if (success) {
            toast.success('群头像修改成功');
            setEditingAvatar(false);
            load();
        } else {
            toast.error('群头像修改失败');
        }
    };

    const handleSaveAnnouncement = async () => {
        if (!token) return;
        const { setGroupAnnouncement } = await import('@/utils/message');
        const success = await setGroupAnnouncement(token, convId, announcement);
        if (success) {
            toast.success('群公告修改成功');
            load();
        } else {
            toast.error('群公告修改失败');
        }
    };

    const handleViewHistoryAnnouncements = async () => {
        if (!token) return;
        setLoadingHistory(true);
        try {
            const announcements = await getGroupAnnouncements(token, convId);
            setHistoryAnnouncements(announcements);
            setShowHistoryAnnouncements(true);
        } catch (err) {
            console.error('获取历史公告失败:', err);
            toast.error('获取历史公告失败');
        } finally {
            setLoadingHistory(false);
        }
    };

    const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        try {
            const form = new FormData();
            form.append('file', f);
            const r = await fetch(`https://${BACKEND_URL}/chat/upload`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
                body: form
            });
            const d = await r.json();
            if (d.code !== 0) {
                toast.error('上传失败: ' + d.info);
                return;
            }
            let url = d.url as string;
            if (url.startsWith('/')) url = `https://${BACKEND_URL}${url}`;
            setNewAvatar(url);
        } catch (err) {
            console.error(err);
            toast.error('上传异常');
        } finally {
            if (fileRef.current) fileRef.current.value = '';
        }
    };

    const handleSetRole = async (userId: number, role: 'admin' | 'member') => {
        if (!token) return;

        const success = await setMemberRole(token, convId, userId, role);
        if (success) {
            const actionText = role === 'admin' ? '设为管理员' : '取消管理员';
            toast.success(`${actionText}成功`);
            // 重新加载数据以更新所有状态
            load();
        } else {
            toast.error('设置失败');
        }
    };

    const handleTransferOwner = async (userId: number) => {
        if (!token || !groupInfo || groupInfo.role !== 'owner') return;
        if (confirm('确定要将群主转让给该成员吗？转让后您将成为普通成员。')) {
            const success = await transferOwner(token, convId, userId);
            if (success) {
                toast.success('群主转让成功');
                // 转让群主后更新本地状态，不刷新页面
                setTimeout(() => {
                    // 重新加载群信息，这会更新当前用户的角色
                    load();
                    // 同时刷新会话列表，确保会话显示正确
                    refreshConversations({ silent: true });
                }, 1000);
            } else {
                toast.error('群主转让失败');
            }
        }
    };

    const handleRemoveMember = async (userId: number) => {
        if (!token || !groupInfo) return;

        const targetMember = groupInfo.members.find(m => m.id === userId);
        if (!targetMember) return;

        // 权限检查
        const isOwner = groupInfo.role === 'owner';
        const isAdmin = groupInfo.role === 'admin';
        const isTargetOwner = targetMember.role === 'owner';
        const isTargetAdmin = targetMember.role === 'admin';

        if (!isOwner && (!isAdmin || isTargetOwner || isTargetAdmin)) {
            toast.error('权限不足，无法移除该成员');
            return;
        }

        if (confirm('确定要移除该成员吗？')) {
            const success = await removeMember(token, convId, userId);
            if (success) {
                toast.success('成员已移除');
                load();
            } else {
                toast.error('移除成员失败，无权限');
            }
        }
    };

    const handleExitGroup = async () => {
        if (!token) return;
        if (confirm('确定要退出该群聊吗？')) {
            const success = await exitGroup(token, convId);
            if (success) {
                onClose();
                window.location.reload();
            }
        }
    };

    const handleDisbandGroup = async () => {
        if (!token || !groupInfo || groupInfo.role !== 'owner') {
            toast.error('权限不足，无法解散群聊');
            return;
        }
        if (confirm('确定要解散该群聊吗？解散后所有成员将被移出群聊，且无法恢复！')) {
            const success = await disbandGroup(token, convId);
            if (success) {
                toast.success('群聊已解散');
                onClose();
                // 延迟一下让WebSocket事件处理完成
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                toast.error('解散群聊失败，请查看控制台日志');
            }
        }
    };

    const handleSetNickname = async (memberId: number, nickname: string) => {
        if (!token) return;
        const { setGroupNickname } = await import('@/utils/message');
        const success = await setGroupNickname(token, convId, nickname);
        if (success) {
            toast.success('群昵称修改成功');
            load();
        } else {
            toast.error('群昵称修改失败');
        }
    };

    // 检查好友关系
    const checkIfFriend = async (userId: number) => {
        if (!token || userId === selfId) return;
        
        // 如果已经检查过，直接返回结果
        if (friendshipStatus[userId] !== undefined) {
            return friendshipStatus[userId];
        }
        
        // 设置正在检查状态
        setCheckingFriendship(prev => ({ ...prev, [userId]: true }));
        
        try {
            const isFriend = await checkFriendship(token, userId);
            setFriendshipStatus(prev => ({ ...prev, [userId]: isFriend }));
            return isFriend;
        } catch (error) {
            console.error('检查好友关系失败:', error);
            return false;
        } finally {
            setCheckingFriendship(prev => ({ ...prev, [userId]: false }));
        }
    };

    // 处理添加好友
    const handleAddFriend = async (userId: number) => {
        if (!token) return;
        
        try {
            const success = await sendFriendRequest(token, userId);
            if (success) {
                toast.success('好友申请已发送');
                // 更新好友状态，避免重复发送
                setFriendshipStatus(prev => ({ ...prev, [userId]: true }));
            } else {
                toast.error('发送好友申请失败');
            }
        } catch (error) {
            console.error('添加好友失败:', error);
            toast.error('添加好友失败');
        }
    };

    // 组件加载时检查所有成员的好友关系
    useEffect(() => {
        if (groupInfo && token) {
            groupInfo.members.forEach(member => {
                if (member.id !== selfId) {
                    checkIfFriend(member.id);
                }
            });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [groupInfo, token, selfId]);

    if (loading) return <div style={{ padding: 16 }}>加载中…</div>;
    if (!groupInfo) return <div style={{ padding: 16 }}>无法加载群信息</div>;

    const isAdmin = groupInfo.role === 'admin' || groupInfo.role === 'owner';
    const isOwner = groupInfo.role === 'owner';

    return (
        <div style={{ width: 360, height: '100%', background: '#fff', borderLeft: '1px solid #e0e0e0', display: 'flex', flexDirection: 'column', position: 'relative', zIndex: 100 }}>
            <div style={{ padding: 12, borderBottom: '1px solid #eee', display: 'flex', alignItems: 'center' }}>
                <div style={{ fontWeight: 600, flex: 1 }}>群聊信息</div>
                <button onClick={onClose} style={{ border: 'none', background: 'transparent', cursor: 'pointer' }}>✕</button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* 群名称和头像 */}
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ width: 60, height: 60, borderRadius: 8, overflow: 'hidden', background: '#eef3ff', display: 'grid', placeItems: 'center' }}>
                        {groupInfo.avatar ? <img src={groupInfo.avatar.startsWith('/') ? `https://${BACKEND_URL}${groupInfo.avatar}` : groupInfo.avatar} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <span style={{ color: '#4f6ef7', fontWeight: 700 }}>{groupInfo.name?.charAt(0) ?? '?'}</span>}
                    </div>
                    <div style={{ flex: 1 }}>
                        {/* 群名称编辑 */}
                        {editingName && isAdmin ? (
                            <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
                                <input
                                    value={newName}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewName(e.target.value)}
                                    style={{ flex: 1, padding: '4px 8px', border: '1px solid #e0e0e0', borderRadius: 4, fontSize: 14 }}
                                />
                                <button onClick={handleSaveName} style={{ padding: '4px 8px', background: '#007aff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>保存</button>
                                <button onClick={() => { setEditingName(false); setNewName(groupInfo.name); }} style={{ padding: '4px 8px', background: '#f0f0f0', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>取消</button>
                            </div>
                        ) : (
                            <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                                <span>{groupInfo.name || '未命名群聊'}</span>
                                {isAdmin && (
                                    <button onClick={() => setEditingName(true)} style={{ fontSize: 12, color: '#007aff', background: 'none', border: 'none', cursor: 'pointer' }}>编辑</button>
                                )}
                            </div>
                        )}
                        
                        {/* 群头像编辑 */}
                        {editingAvatar && isAdmin ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                <div style={{ display: 'flex', gap: 4 }}>
                                    <input
                                        value={newAvatar}
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewAvatar(e.target.value)}
                                        placeholder="图片URL"
                                        style={{ flex: 1, padding: '4px 8px', border: '1px solid #e0e0e0', borderRadius: 4, fontSize: 14 }}
                                    />
                                    <button onClick={handleSaveAvatar} style={{ padding: '4px 8px', background: '#007aff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>保存</button>
                                    <button onClick={() => { setEditingAvatar(false); setNewAvatar(groupInfo.avatar); }} style={{ padding: '4px 8px', background: '#f0f0f0', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>取消</button>
                                </div>
                                <label style={{
                                    padding: '4px 8px',
                                    background: '#f0f0f0',
                                    border: '1px solid #e0e0e0',
                                    borderRadius: 4,
                                    cursor: 'pointer',
                                    fontSize: 12,
                                    display: 'inline-block',
                                    width: 'fit-content'
                                }}>
                                    上传图片
                                    <input
                                        ref={fileRef}
                                        type="file"
                                        accept="image/*"
                                        style={{ display: "none" }}
                                        onChange={handleAvatarUpload}
                                    />
                                </label>
                            </div>
                        ) : (
                            <div style={{ fontSize: 12, color: '#666' }}>
                                {isAdmin && (
                                    <button onClick={() => setEditingAvatar(true)} style={{ fontSize: 12, color: '#007aff', background: 'none', border: 'none', cursor: 'pointer' }}>编辑头像</button>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* 群公告 */}
                <div>
                    <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>群公告</div>
                    {isAdmin ? (
                        <>
                            <textarea 
                                value={announcement} 
                                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setAnnouncement(e.target.value)} 
                                placeholder="没有设置群公告"
                                style={{ width: '100%', minHeight: 64, padding: '10px 12px', border: '1px solid #e0e0e0', borderRadius: 10, outline: 'none', resize: 'vertical' }} 
                            />
                            <div style={{ marginTop: 8 }}>
                                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                    <button onClick={handleSaveAnnouncement} style={{ background: '#007aff', color: '#fff', border: 'none', borderRadius: 8, padding: '6px 12px', cursor: 'pointer' }}>保存公告</button>
                                    <button
                                        onClick={handleViewHistoryAnnouncements}
                                        disabled={loadingHistory}
                                        style={{
                                            background: '#f0f0f0',
                                            color: '#333',
                                            border: '1px solid #ddd',
                                            borderRadius: 8,
                                            padding: '6px 12px',
                                            cursor: loadingHistory ? 'not-allowed' : 'pointer',
                                            fontSize: 12
                                        }}
                                    >
                                        {loadingHistory ? '加载中...' : '查看历史公告'}
                                    </button>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            <div style={{ padding: '10px 12px', border: '1px solid #f0f0f0', borderRadius: 10, color: announcement ? '#111' : '#999' }}>
                                {announcement || '没有设置群公告'}
                            </div>
                            <button
                                onClick={handleViewHistoryAnnouncements}
                                disabled={loadingHistory}
                                style={{
                                    background: '#f0f0f0',
                                    color: '#333',
                                    border: '1px solid #ddd',
                                    borderRadius: 8,
                                    padding: '6px 12px',
                                    cursor: loadingHistory ? 'not-allowed' : 'pointer',
                                    fontSize: 12,
                                    alignSelf: 'flex-end'
                                }}
                            >
                                {loadingHistory ? '加载中...' : '查看历史公告'}
                            </button>
                        </div>
                    )}
                </div>

                {/* 成员列表 */}
                <div>
                    <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>群成员（{groupInfo.members.length}）</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 320, overflow: 'auto' }}>
                        {groupInfo.members.map((m: {id: number, nickname: string, avatar?: string, role: string, is_active?: boolean}) => {
                            // 判断成员角色
                            const isMemberOwner = m.role === 'owner';
                            const isMemberAdmin = m.role === 'admin';

                            // 获取当前用户信息
                            const isSelf = m.id === selfId;
                            
                            // 检查是否是好友
                            const isFriend = friendshipStatus[m.id] || false;
                            const isCheckingFriend = checkingFriendship[m.id] || false;

                            // 权限判断 - 普通成员没有任何管理权限
                            const canManageRole = isOwner && !isMemberOwner && !isSelf; // 只有群主能管理角色，不能给自己和群主管理
                            const canTransferOwner = isOwner && !isMemberOwner && !isSelf; // 只有群主能转让，不能转让给自己
                            let canRemoveMember = ((isOwner && !isMemberOwner && !isSelf) || (isAdmin && !isMemberOwner && !isMemberAdmin && !isSelf)); // 不能删除自己、群主和管理员

                            // 额外检查：管理员绝对不能移除群主
                            if (isAdmin && isMemberOwner) {
                                canRemoveMember = false;
                            }
                            
                            // 判断是否显示添加好友按钮：不是自己、不是好友、用户活跃
                            const canAddFriend = !isSelf && !isFriend && m.is_active !== false;

                            return (
                                <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 8, background: '#f9f9f9', borderRadius: 8 }}>
                                    <div style={{ width: 32, height: 32, borderRadius: 6, overflow: 'hidden', background: '#eee' }}>
                                        {m.avatar ? <img src={m.avatar.startsWith('/') ? `https://${BACKEND_URL}${m.avatar}` : m.avatar} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : null}
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        {/* 编辑昵称界面 */}
                                        {isSelf && editingNickname ? (
                                            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                                                <input
                                                    type="text"
                                                    value={newNickname}
                                                    onChange={(e) => setNewNickname(e.target.value)}
                                                    placeholder="输入群昵称"
                                                    style={{ flex: 1, padding: '4px 8px', border: '1px solid #e0e0e0', borderRadius: 4, fontSize: 14 }}
                                                    maxLength={30}
                                                />
                                                <button
                                                    onClick={() => {
                                                        handleSetNickname(m.id, newNickname);
                                                        setEditingNickname(false);
                                                    }}
                                                    style={{ fontSize: 11, padding: '4px 8px', background: '#007aff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
                                                >
                                                    保存
                                                </button>
                                                <button
                                                    onClick={() => {
                                                        setEditingNickname(false);
                                                        setNewNickname(m.nickname);
                                                    }}
                                                    style={{ fontSize: 11, padding: '4px 8px', background: '#f0f0f0', border: 'none', borderRadius: 4, cursor: 'pointer' }}
                                                >
                                                    取消
                                                </button>
                                            </div>
                                        ) : (
                                            <div style={{ fontSize: 14, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6 }}>
                                                <span>{m.nickname || `用户#${m.id}`}</span>
                                                {m.is_active === false && <span style={{ color: 'red', fontSize: '0.8em' }}>(已注销)</span>}
                                                {isMemberOwner && (
                                                    <span style={{ fontSize: 11, color: '#007aff', background: '#e3f2fd', padding: '2px 6px', borderRadius: 4 }}>群主</span>
                                                )}
                                                {isMemberAdmin && (
                                                    <span style={{ fontSize: 11, color: '#ff9500', background: '#fff3e0', padding: '2px 6px', borderRadius: 4 }}>管理员</span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                                        {/* 编辑昵称按钮 - 仅对当前用户显示 */}
                                        {isSelf && !editingNickname && (
                                            <button
                                                onClick={() => {
                                                    setEditingNickname(true);
                                                    setNewNickname(m.nickname);
                                                }}
                                                style={{ fontSize: 11, padding: '4px 8px', background: '#f0f0f0', border: 'none', borderRadius: 4, cursor: 'pointer' }}
                                            >
                                                编辑昵称
                                            </button>
                                        )}
                                        
                                        {/* 添加好友按钮 - 仅对非好友且非自己的成员显示 */}
                                        {canAddFriend && (
                                            <button
                                                onClick={() => handleAddFriend(m.id)}
                                                disabled={isCheckingFriend}
                                                style={{
                                                    fontSize: 11,
                                                    padding: '4px 8px',
                                                    background: '#34c759',
                                                    color: '#fff',
                                                    border: 'none',
                                                    borderRadius: 4,
                                                    cursor: isCheckingFriend ? 'not-allowed' : 'pointer',
                                                    opacity: isCheckingFriend ? 0.6 : 1
                                                }}
                                            >
                                                {isCheckingFriend ? '检查中...' : '添加好友'}
                                            </button>
                                        )}
                                        
                                        {/* 管理员操作按钮 */}
                                        {(canManageRole || canTransferOwner || canRemoveMember) && (
                                            <>
                                                {canManageRole && (
                                                    <button
                                                        onClick={() => handleSetRole(m.id, isMemberAdmin ? 'member' : 'admin')}
                                                        style={{ fontSize: 11, padding: '4px 8px', background: '#f0f0f0', border: 'none', borderRadius: 4, cursor: 'pointer' }}
                                                    >
                                                        {isMemberAdmin ? '移除管理员' : '设为管理员'}
                                                    </button>
                                                )}
                                                {canTransferOwner && (
                                                    <button
                                                        onClick={() => handleTransferOwner(m.id)}
                                                        style={{ fontSize: 11, padding: '4px 8px', background: '#007aff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
                                                    >
                                                        转让群主
                                                    </button>
                                                )}
                                                {canRemoveMember && (
                                                    <button
                                                        onClick={() => handleRemoveMember(m.id)}
                                                        style={{ fontSize: 11, padding: '4px 8px', background: '#ff3b30', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
                                                    >
                                                        移除
                                                    </button>
                                                )}
                                            </>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* 邀请好友按钮（所有成员可见） */}
                <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                    <button
                        onClick={() => setShowInviteModal(true)}
                        style={{
                            flex: 1,
                            padding: '10px',
                            background: '#007aff',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 8,
                            cursor: 'pointer',
                            fontWeight: 500,
                            fontSize: 14
                        }}
                    >
                        邀请好友
                    </button>
                    
                    {/* 邀请管理按钮（仅群主和管理员可见） */}
                    {isAdmin && (
                        <button
                            onClick={() => setShowInvitationsPanel(true)}
                            style={{
                                flex: 1,
                                padding: '10px',
                                background: '#f0f0f0',
                                color: '#333',
                                border: '1px solid #ddd',
                                borderRadius: 8,
                                cursor: 'pointer',
                                fontWeight: 500,
                                fontSize: 14
                            }}
                        >
                            邀请管理
                        </button>
                    )}
                </div>

                {/* 解散群聊（仅群主可见） */}
                {isOwner && (
                    <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid #eee' }}>
                        <button
                            onClick={handleDisbandGroup}
                            style={{ width: '100%', padding: '10px', background: '#dc3545', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 500, marginBottom: 8 }}
                        >
                            解散群聊
                        </button>
                    </div>
                )}

                {/* 退出群聊（群主不显示）- 只要不是群主都应该显示退出按钮 */}
                {!isOwner && groupInfo.members.length >= 1 && (
                    <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid #eee' }}>
                        <button
                            onClick={handleExitGroup}
                            style={{ width: '100%', padding: '10px', background: '#ff3b30', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 500 }}
                        >
                            退出群聊
                        </button>
                    </div>
                )}
            </div>
            
            {/* 历史公告弹窗 */}
            {showHistoryAnnouncements && (
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
                        maxWidth: 600,
                        maxHeight: '80%',
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden'
                    }}>
                        {/* 弹窗标题 */}
                        <div style={{
                            padding: 16,
                            borderBottom: '1px solid #eee',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between'
                        }}>
                            <div style={{ fontSize: 16, fontWeight: 600 }}>历史群公告</div>
                            <button
                                onClick={() => setShowHistoryAnnouncements(false)}
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
                        
                        {/* 历史公告列表 */}
                        <div style={{
                            flex: 1,
                            overflowY: 'auto',
                            padding: 16
                        }}>
                            {historyAnnouncements.length === 0 ? (
                                <div style={{
                                    textAlign: 'center',
                                    color: '#999',
                                    padding: 40
                                }}>
                                    暂无历史公告
                                </div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                    {historyAnnouncements.map((announce) => (
                                        <div key={announce.id} style={{
                                            border: '1px solid #f0f0f0',
                                            borderRadius: 8,
                                            padding: 12
                                        }}>
                                            <div style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center',
                                                marginBottom: 8
                                            }}>
                                                <div style={{
                                                    fontSize: 12,
                                                    color: '#666'
                                                }}>
                                                    {announce.author_nickname || announce.author_name}
                                                </div>
                                                <div style={{
                                                    fontSize: 12,
                                                    color: '#999'
                                                }}>
                                                    {new Date(announce.created_at).toLocaleString()}
                                                </div>
                                            </div>
                                            <div style={{
                                                fontSize: 14,
                                                lineHeight: 1.5,
                                                color: '#333',
                                                whiteSpace: 'pre-wrap'
                                            }}>
                                                {announce.content}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
            
            {/* 邀请好友弹窗 */}
            <InviteFriendModal
                isOpen={showInviteModal}
                onClose={() => setShowInviteModal(false)}
                groupId={convId}
                groupName={groupInfo.name || '未命名群聊'}
                groupMembers={groupInfo.members.map(m => m.id)}
            />
            
            {/* 邀请管理面板 */}
            <GroupInvitationsPanel
                isOpen={showInvitationsPanel}
                onClose={() => setShowInvitationsPanel(false)}
                groupId={convId}
                groupName={groupInfo.name || '未命名群聊'}
                isOwner={isOwner}
                isAdmin={isAdmin}
            />
        </div>
    );
}

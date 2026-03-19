"use client";

import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { BACKEND_URL } from '@/constant/strings';
import { useUserContext } from '@/context/UserContext';
import { getGroupInvitations, reviewGroupInvitation, GroupInvitation } from '@/utils/message';

interface GroupInvitationsPanelProps {
    isOpen: boolean;
    onClose: () => void;
    groupId: number;
    groupName: string;
    isOwner: boolean;
    isAdmin: boolean;
}

export default function GroupInvitationsPanel({ 
    isOpen, 
    onClose, 
    groupId, 
    groupName, 
    isOwner, 
    isAdmin 
}: GroupInvitationsPanelProps) {
    const { token } = useUserContext();
    const [invitations, setInvitations] = useState<GroupInvitation[]>([]);
    const [loading, setLoading] = useState(true);
    const [reviewing, setReviewing] = useState<number | null>(null);
    const [activeTab, setActiveTab] = useState<'pending' | 'all'>('pending');
    const [reviewComment, setReviewComment] = useState('');
    const [showReviewDialog, setShowReviewDialog] = useState<{
        show: boolean;
        invitationId: number;
        action: 'approve' | 'reject';
        inviterName: string;
        inviteeName: string;
    }>({
        show: false,
        invitationId: 0,
        action: 'approve',
        inviterName: '',
        inviteeName: ''
    });

    // 加载邀请列表
    useEffect(() => {
        if (!isOpen || !token) return;

        const loadInvitations = async () => {
            setLoading(true);
            try {
                const status = activeTab === 'pending' ? 'pending' : undefined;
                const invitationList = await getGroupInvitations(token, groupId, status);
                setInvitations(invitationList);
            } catch (error) {
                console.error('加载邀请列表失败:', error);
                toast.error('加载邀请列表失败');
            } finally {
                setLoading(false);
            }
        };

        loadInvitations();
    }, [isOpen, token, groupId, activeTab]);

    // 处理审核邀请
    const handleReviewInvitation = async () => {
        if (!token || !showReviewDialog.show) return;

        setReviewing(showReviewDialog.invitationId);
        try {
            const result = await reviewGroupInvitation(
                token,
                showReviewDialog.invitationId,
                showReviewDialog.action,
                reviewComment
            );
            
            if (result.success) {
                const actionText = showReviewDialog.action === 'approve' ? '通过' : '拒绝';
                toast.success(`已${actionText} ${showReviewDialog.inviterName} 邀请 ${showReviewDialog.inviteeName} 的申请`);
                
                // 刷新邀请列表
                const status = activeTab === 'pending' ? 'pending' : undefined;
                const invitationList = await getGroupInvitations(token, groupId, status);
                setInvitations(invitationList);
                
                // 关闭对话框
                setShowReviewDialog({ show: false, invitationId: 0, action: 'approve', inviterName: '', inviteeName: '' });
                setReviewComment('');
            } else {
                toast.error(result.error || '审核失败');
            }
        } catch (error) {
            console.error('审核邀请失败:', error);
            toast.error('审核失败，请重试');
        } finally {
            setReviewing(null);
        }
    };

    // 打开审核对话框
    const openReviewDialog = (invitation: GroupInvitation, action: 'approve' | 'reject') => {
        setShowReviewDialog({
            show: true,
            invitationId: invitation.id,
            action,
            inviterName: invitation.inviter_nickname || invitation.inviter_name,
            inviteeName: invitation.invitee_nickname || invitation.invitee_name
        });
    };

    // 获取状态标签样式
    const getStatusStyle = (status: string) => {
        switch (status) {
            case 'pending':
                return { color: '#ff9500', background: '#fff3e0' };
            case 'approved':
                return { color: '#52c41a', background: '#f6ffed' };
            case 'rejected':
                return { color: '#ff4d4f', background: '#fff2f0' };
            case 'expired':
                return { color: '#999', background: '#f5f5f5' };
            default:
                return { color: '#999', background: '#f5f5f5' };
        }
    };

    // 获取状态文本
    const getStatusText = (status: string) => {
        switch (status) {
            case 'pending':
                return '待审核';
            case 'approved':
                return '已通过';
            case 'rejected':
                return '已拒绝';
            case 'expired':
                return '已过期';
            default:
                return '未知';
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
                maxWidth: 700,
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
                        群聊邀请管理 - {groupName}
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
                
                {/* 标签页 */}
                <div style={{
                    display: 'flex',
                    borderBottom: '1px solid #f0f0f0'
                }}>
                    <button
                        onClick={() => setActiveTab('pending')}
                        style={{
                            flex: 1,
                            padding: '12px 16px',
                            border: 'none',
                            background: activeTab === 'pending' ? '#f0f8ff' : 'white',
                            borderBottom: activeTab === 'pending' ? '2px solid #007aff' : 'none',
                            cursor: 'pointer',
                            fontSize: 14,
                            fontWeight: activeTab === 'pending' ? 500 : 400
                        }}
                    >
                        待审核
                    </button>
                    <button
                        onClick={() => setActiveTab('all')}
                        style={{
                            flex: 1,
                            padding: '12px 16px',
                            border: 'none',
                            background: activeTab === 'all' ? '#f0f8ff' : 'white',
                            borderBottom: activeTab === 'all' ? '2px solid #007aff' : 'none',
                            cursor: 'pointer',
                            fontSize: 14,
                            fontWeight: activeTab === 'all' ? 500 : 400
                        }}
                    >
                        全部记录
                    </button>
                </div>
                
                {/* 邀请列表 */}
                <div style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: 16
                }}>
                    {loading ? (
                        <div style={{ textAlign: 'center', padding: 20 }}>加载中...</div>
                    ) : invitations.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                            {activeTab === 'pending' ? '暂无待审核的邀请' : '暂无邀请记录'}
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {invitations.map((invitation) => (
                                <div
                                    key={invitation.id}
                                    style={{
                                        border: '1px solid #f0f0f0',
                                        borderRadius: 8,
                                        padding: 16,
                                        backgroundColor: 'white'
                                    }}
                                >
                                    {/* 邀请信息头部 */}
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        marginBottom: 12
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                            <span style={{ fontWeight: 500 }}>
                                                {invitation.inviter_nickname || invitation.inviter_name} 邀请 {invitation.invitee_nickname || invitation.invitee_name}
                                            </span>
                                            <span style={{
                                                padding: '2px 8px',
                                                borderRadius: 4,
                                                fontSize: 12,
                                                ...getStatusStyle(invitation.status)
                                            }}>
                                                {getStatusText(invitation.status)}
                                            </span>
                                        </div>
                                        <div style={{ fontSize: 12, color: '#999' }}>
                                            {new Date(invitation.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                    
                                    {/* 邀请附言 */}
                                    {invitation.message && (
                                        <div style={{
                                            backgroundColor: '#f9f9f9',
                                            padding: 8,
                                            borderRadius: 6,
                                            fontSize: 14,
                                            marginBottom: 12,
                                            color: '#666'
                                        }}>
                                            {invitation.message}
                                        </div>
                                    )}
                                    
                                    {/* 审核信息 */}
                                    {(invitation.reviewer_name || invitation.review_comment) && (
                                        <div style={{
                                            backgroundColor: '#f0f8ff',
                                            padding: 8,
                                            borderRadius: 6,
                                            fontSize: 12,
                                            marginBottom: 12
                                        }}>
                                            {invitation.reviewer_name && (
                                                <div style={{ marginBottom: 4 }}>
                                                    审核人：{invitation.reviewer_nickname || invitation.reviewer_name}
                                                </div>
                                            )}
                                            {invitation.review_comment && (
                                                <div>
                                                    审核意见：{invitation.review_comment}
                                                </div>
                                            )}
                                            {invitation.review_time && (
                                                <div style={{ color: '#999', marginTop: 4 }}>
                                                    审核时间：{new Date(invitation.review_time).toLocaleString()}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    
                                    {/* 操作按钮 */}
                                    {invitation.status === 'pending' && (isOwner || isAdmin) && (
                                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                                            <button
                                                onClick={() => openReviewDialog(invitation, 'reject')}
                                                disabled={reviewing === invitation.id}
                                                style={{
                                                    padding: '6px 12px',
                                                    border: '1px solid #e0e0e0',
                                                    borderRadius: 6,
                                                    background: 'white',
                                                    cursor: reviewing === invitation.id ? 'not-allowed' : 'pointer',
                                                    fontSize: 12
                                                }}
                                            >
                                                拒绝
                                            </button>
                                            <button
                                                onClick={() => openReviewDialog(invitation, 'approve')}
                                                disabled={reviewing === invitation.id}
                                                style={{
                                                    padding: '6px 12px',
                                                    border: 'none',
                                                    borderRadius: 6,
                                                    background: reviewing === invitation.id ? '#ccc' : '#007aff',
                                                    color: 'white',
                                                    cursor: reviewing === invitation.id ? 'not-allowed' : 'pointer',
                                                    fontSize: 12
                                                }}
                                            >
                                                {reviewing === invitation.id ? '处理中...' : '通过'}
                                            </button>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
            
            {/* 审核对话框 */}
            {showReviewDialog.show && (
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
                    zIndex: 2000
                }}>
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: 12,
                        width: '90%',
                        maxWidth: 400,
                        padding: 20
                    }}>
                        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
                            {showReviewDialog.action === 'approve' ? '通过邀请' : '拒绝邀请'}
                        </div>
                        <div style={{ marginBottom: 16 }}>
                            确认要{showReviewDialog.action === 'approve' ? '通过' : '拒绝'} {showReviewDialog.inviterName} 邀请 {showReviewDialog.inviteeName} 的申请吗？
                        </div>
                        <div style={{ marginBottom: 16 }}>
                            <textarea
                                placeholder="审核意见（可选）"
                                value={reviewComment}
                                onChange={(e) => setReviewComment(e.target.value)}
                                style={{
                                    width: '100%',
                                    minHeight: 80,
                                    padding: '10px 12px',
                                    border: '1px solid #e0e0e0',
                                    borderRadius: 8,
                                    outline: 'none',
                                    resize: 'vertical',
                                    fontSize: 14
                                }}
                            />
                        </div>
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => {
                                    setShowReviewDialog({ show: false, invitationId: 0, action: 'approve', inviterName: '', inviteeName: '' });
                                    setReviewComment('');
                                }}
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
                                onClick={handleReviewInvitation}
                                disabled={reviewing === showReviewDialog.invitationId}
                                style={{
                                    padding: '8px 16px',
                                    border: 'none',
                                    borderRadius: 8,
                                    background: reviewing === showReviewDialog.invitationId ? '#ccc' : '#007aff',
                                    color: 'white',
                                    cursor: reviewing === showReviewDialog.invitationId ? 'not-allowed' : 'pointer',
                                    fontSize: 14
                                }}
                            >
                                确认
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
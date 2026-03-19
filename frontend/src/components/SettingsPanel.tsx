"use client";

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BACKEND_URL } from '@/constant/strings';
import { useUserContext } from '@/context/UserContext';
import PasswordStrengthIndicator from './PasswordStrengthIndicator';
import { validatePasswordStrength } from '@/utils/passwordValidator';
import { validateUsername, getUsernameRequirements, UsernameValidationResult } from '@/utils/usernameValidator';
import { toast } from 'react-toastify';

export default function SettingsPanel() {
    const { logout, setSelfAvatar, refreshConversations, setUsername: setGlobalUsername, update_id_to_username, selfId } = useUserContext();
    const [loading, setLoading] = useState(true);

    const [username, setUsername] = useState('');
    const [usernameValidation, setUsernameValidation] = useState<UsernameValidationResult | null>(null);
    const [showUsernameRequirements, setShowUsernameRequirements] = useState(false);
    const [avatar, setAvatar] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [info, setInfo] = useState('');

    const [oldPwd, setOldPwd] = useState('');
    const [newPwd, setNewPwd] = useState('');
    const [confirmNewPwd, setConfirmNewPwd] = useState('');
    const [showOldPwd, setShowOldPwd] = useState(false); // 显示/隐藏原密码
    const [showNewPwd, setShowNewPwd] = useState(false); // 显示/隐藏新密码
    const [showConfirmNewPwd, setShowConfirmNewPwd] = useState(false); // 显示/隐藏确认新密码

    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [deletePassword, setDeletePassword] = useState('');

    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const fileRef = useRef<HTMLInputElement | null>(null);

    const loadSelf = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        try {
            const r = await fetch(`https://${BACKEND_URL}/account/get_info`, { headers: { Authorization: `Bearer ${token}` } });
            const d = await r.json();
            if (d.code === 0) {
                setUsername(d.username || '');
                const ava = (d.avatar || '') as string;
                setAvatar(ava.startsWith('/') ? `https://${BACKEND_URL}${ava}` : ava);
                setEmail(d.email || '');
                setPhone(d.phone || '');
                setInfo(d.info || '');
            }
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => { loadSelf(); }, [loadSelf]);

    // 用户名变化时验证格式
    useEffect(() => {
        if (username) {
            const validation = validateUsername(username);
            setUsernameValidation(validation);
        } else {
            setUsernameValidation(null);
        }
    }, [username]);

    // 通用修改函数
    async function saveField(field: string, value: string, currentPassword: string) {
        if (!token) return;

        // 需要原密码的改动统一做空校验
        if ((field === 'email' || field === 'phone' || field === 'password') && !currentPassword) {
            toast.error('请先输入正确的原密码');
            return;
        }

        // 如果是修改密码，进行前端验证
        if (field === 'password') {
            // 检查是否输入了新密码
            if (!value) {
                toast.error('请输入新密码');
                return;
            }
            
            // 检查是否确认了新密码
            if (!confirmNewPwd) {
                toast.error('请再次输入新密码进行确认');
                return;
            }
            
            // 验证新密码强度
            const validation = validatePasswordStrength(value);
            if (!validation.isValid) {
                toast.error('新密码不符合要求：' + validation.errors.join('，'));
                return;
            }

            // 验证两次输入的密码是否一致
            if (value !== confirmNewPwd) {
                toast.error('两次输入的新密码不一致');
                return;
            }
        }

        // 如果是修改用户名，进行前端验证
        if (field === 'username') {
            const validation = validateUsername(value);
            if (!validation.isValid) {
                toast.error('用户名不符合要求：' + validation.errors.join('，'));
                return;
            }
        }

        try {
            const r = await fetch(`https://${BACKEND_URL}/account/edit_info`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ field, value, password: currentPassword })
            });
            const d = await r.json();
            if (d.code !== 0) {
                toast.error(`修改 ${field} 失败: ${d.info}`);
            } else {
                toast.success(`修改 ${field} 成功`);
                if (field === 'avatar') setSelfAvatar(value);
                if (field === 'username') {
                    setGlobalUsername(value);
                    localStorage.setItem('username', value);
                    if (selfId) {
                        update_id_to_username(selfId, { id: selfId, name: value, avatar, info, is_active: true });
                    }
                    void refreshConversations({ silent: true });
                }
                if (field === 'password') {
                    // 密码修改成功后清空密码字段
                    setOldPwd('');
                    setNewPwd('');
                    setConfirmNewPwd('');
                }
            }
        } catch (err) {
            console.error(err);
            toast.error('请求失败，请稍后再试');
        }
    }
    async function handleDeleteAccount() {
        if (!token) return;
        if (!deletePassword) {
            toast.error('请输入密码以确认注销');
            return;
        }
        try {
            const r = await fetch(`https://${BACKEND_URL}/account/delete_account`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ password: deletePassword })
            });
            const d = await r.json();
            if (d.code === 0) {
                toast.success('账号已注销');
                logout();
            } else {
                toast.error('注销失败: ' + d.info);
            }
        } catch (err) {
            console.error(err);
            toast.error('请求异常');
        }
    }
    if (loading) return <div style={{ padding: 20 }}>加载中…</div>;

    const passwordValidation = validatePasswordStrength(newPwd);
    // 移除按钮禁用逻辑，改为在点击时进行验证
    // const canSubmitPassword = Boolean(
    //     oldPwd &&
    //     newPwd &&
    //     confirmNewPwd &&
    //     newPwd === confirmNewPwd &&
    //     passwordValidation.isValid
    // );

    const fieldWrap: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: 8 };
    const labelStyle: React.CSSProperties = { fontSize: 13, color: '#6b7280' };
    const inputStyle: React.CSSProperties = {
        width: '100%', maxWidth: 480, padding: '10px 12px',
        borderRadius: 12, border: '1px solid #e5e7eb', outline: 'none',
        fontSize: 14, background: '#fff', boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
    };
    const btnStyle: React.CSSProperties = {
        padding: '10px 14px', borderRadius: 10, border: '1px solid #dbeafe',
        background: '#eff6ff', color: '#1d4ed8', cursor: 'pointer', fontWeight: 600
    };

    return (
        <div style={{ padding: 16 }}>
            <div style={{ maxWidth: 720, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 18 }}>

                {/* 头像 */}
                <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                    <div style={{ width: 64, height: 64, borderRadius: 12, overflow: 'hidden', background: '#f3f4f6', display: 'grid', placeItems: 'center' }}>
                        {avatar ? <img src={avatar} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <span style={{ color: '#9ca3af' }}>无头像</span>}
                    </div>
                    <div style={{ ...fieldWrap, flex: 1 }}>
                        <div style={labelStyle}>头像</div>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                            <label title="从本地上传头像" style={{ ...btnStyle, background: '#fff', border: '1px solid #e5e7eb', color: '#374151', cursor: 'pointer' }}>
                                上传图片
                                <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={async (e) => {
                                    const f = e.target.files?.[0]; if (!f) return;
                                    try {
                                        const form = new FormData();
                                        form.append('file', f);
                                        const r = await fetch(`https://${BACKEND_URL}/chat/upload`, {
                                            method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form
                                        });
                                        const d = await r.json();
                                        if (d.code !== 0) return alert('上传失败: ' + d.info);
                                        let url = d.url as string; if (url.startsWith('/')) url = `https://${BACKEND_URL}${url}`;
                                        setAvatar(url);
                                        await saveField('avatar', url, '');
                                    } catch (err) { console.error(err); alert('上传异常'); }
                                    finally { if (fileRef.current) fileRef.current.value = ''; }
                                }} />
                            </label>
                            <span style={{ fontSize: 12, color: '#6b7280' }}>上传后自动保存</span>
                        </div>
                    </div>
                </div>

                {/* 用户名 */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'end', gap: 12 }}>
                    <div style={fieldWrap}>
                        <div style={labelStyle}>用户名</div>
                        <input
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            onFocus={() => setShowUsernameRequirements(true)}
                            onBlur={() => setShowUsernameRequirements(false)}
                            style={{ ...inputStyle, maxWidth: 620 }}
                            placeholder="请输入用户名"
                        />
                        {showUsernameRequirements && (
                            <div style={{
                                marginTop: 8,
                                padding: 10,
                                backgroundColor: '#f8f9fa',
                                borderRadius: 6,
                                fontSize: 12,
                                color: '#666'
                            }}>
                                <div style={{ fontWeight: 600, marginBottom: 6, color: '#333' }}>用户名格式要求：</div>
                                {getUsernameRequirements().map((requirement, index) => (
                                    <div key={index} style={{ marginBottom: 2 }}>
                                        • {requirement}
                                    </div>
                                ))}
                            </div>
                        )}
                        {usernameValidation && usernameValidation.errors.length > 0 && (
                            <div style={{ marginTop: 8, color: '#ff4d4f', fontSize: 12 }}>
                                {usernameValidation.errors.map((error, index) => (
                                    <div key={index} style={{ marginBottom: 2 }}>
                                        • {error}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    <button
                        onClick={() => saveField('username', username, '')}
                        style={btnStyle}
                        disabled={usernameValidation !== null && !usernameValidation.isValid}
                    >
                        保存
                    </button>
                </div>

                {/* 个性签名 */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'end', gap: 12 }}>
                    <div style={fieldWrap}>
                        <div style={labelStyle}>个性签名</div>
                        <input
                            value={info}
                            onChange={e => {
                                if (e.target.value.length <= 100) {
                                    setInfo(e.target.value);
                                }
                            }}
                            maxLength={100}
                            style={{ ...inputStyle, maxWidth: 620 }}
                            placeholder="一句话介绍自己"
                        />
                        <div style={{ fontSize: 12, color: '#6b7280', textAlign: 'right', marginTop: 4 }}>
                            {info.length}/100
                        </div>
                    </div>
                    <button onClick={() => saveField('info', info, '')} style={btnStyle}>保存</button>
                </div>

                {/* 安全设置 */}
                <div style={{ marginTop: 16, padding: 12, borderTop: '1px solid #eef2f7', display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div style={{ fontWeight: 700 }}>安全设置（修改需要原密码）</div>

                    {/* 原密码 */}
                    <div style={fieldWrap}>
                        <div style={labelStyle}>原密码</div>
                        <div style={{ position: 'relative' }}>
                            <input
                                type={showOldPwd ? 'text' : 'password'}
                                value={oldPwd}
                                onChange={e => setOldPwd(e.target.value)}
                                style={{ ...inputStyle, paddingRight: 40 }}
                                placeholder="请输入原密码"
                            />
                            <button
                                type="button"
                                onClick={() => setShowOldPwd(!showOldPwd)}
                                style={{
                                    position: 'absolute',
                                    right: 8,
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    background: 'transparent',
                                    border: 'none',
                                    cursor: 'pointer',
                                    fontSize: 14,
                                    color: '#6b7280'
                                }}
                            >
                                {showOldPwd ? '隐藏' : '显示'}
                            </button>
                        </div>
                    </div>

                    {/* 邮箱 */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'end', gap: 12 }}>
                        <div style={fieldWrap}>
                            <div style={labelStyle}>邮箱</div>
                            <input value={email} onChange={e => setEmail(e.target.value)} style={inputStyle} placeholder="name@example.com" />
                        </div>
                        <button onClick={() => saveField('email', email, oldPwd)} style={btnStyle}>保存</button>
                    </div>

                    {/* 手机 */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'end', gap: 12 }}>
                        <div style={fieldWrap}>
                            <div style={labelStyle}>手机</div>
                            <input value={phone} onChange={e => setPhone(e.target.value)} style={inputStyle} placeholder="仅自己可见" />
                        </div>
                        <button onClick={() => saveField('phone', phone, oldPwd)} style={btnStyle}>保存</button>
                    </div>

                    {/* 新密码 */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'end', gap: 12 }}>
                        <div style={fieldWrap}>
                            <div style={labelStyle}>新密码</div>
                            <div style={{ position: 'relative' }}>
                                <input
                                    type={showNewPwd ? 'text' : 'password'}
                                    value={newPwd}
                                    onChange={e => setNewPwd(e.target.value)}
                                    style={{ ...inputStyle, paddingRight: 40 }}
                                    placeholder="请输入新密码"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowNewPwd(!showNewPwd)}
                                    style={{
                                        position: 'absolute',
                                        right: 8,
                                        top: '50%',
                                        transform: 'translateY(-50%)',
                                        background: 'transparent',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontSize: 14,
                                        color: '#6b7280'
                                    }}
                                >
                                    {showNewPwd ? '隐藏' : '显示'}
                                </button>
                            </div>
                            <PasswordStrengthIndicator password={newPwd} />
                        </div>
                        <button
                            onClick={() => saveField('password', newPwd, oldPwd)}
                            style={btnStyle}
                        >
                            修改密码
                        </button>
                    </div>

                    {/* 确认新密码 */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'end', gap: 12 }}>
                        <div style={fieldWrap}>
                            <div style={labelStyle}>确认新密码</div>
                            <div style={{ position: 'relative' }}>
                                <input
                                    type={showConfirmNewPwd ? 'text' : 'password'}
                                    value={confirmNewPwd}
                                    onChange={e => setConfirmNewPwd(e.target.value)}
                                    style={{ ...inputStyle, paddingRight: 40 }}
                                    placeholder="请再次输入新密码"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmNewPwd(!showConfirmNewPwd)}
                                    style={{
                                        position: 'absolute',
                                        right: 8,
                                        top: '50%',
                                        transform: 'translateY(-50%)',
                                        background: 'transparent',
                                        border: 'none',
                                        cursor: 'pointer',
                                        fontSize: 14,
                                        color: '#6b7280'
                                    }}
                                >
                                    {showConfirmNewPwd ? '隐藏' : '显示'}
                                </button>
                            </div>
                            {confirmNewPwd && newPwd && confirmNewPwd !== newPwd && (
                                <div style={{ color: '#ff4d4f', fontSize: '12px', marginTop: '4px' }}>
                                    两次输入的密码不一致
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* 退出登录与注销 */}
                <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                    <button onClick={logout} style={{ padding: '10px 14px', borderRadius: 10, border: '1px solid #e5e7eb', background: '#f3f4f6', color: '#374151', fontWeight: 600, cursor: 'pointer' }}>退出登录</button>
                    <button onClick={() => setShowDeleteConfirm(true)} style={{ padding: '10px 14px', borderRadius: 10, border: '1px solid #fecaca', background: '#fee2e2', color: '#b91c1c', fontWeight: 700, cursor: 'pointer' }}>注销账号</button>
                </div>

                {/* 注销确认弹窗 */}
                {showDeleteConfirm && (
                    <div style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999
                    }}>
                        <div style={{ background: '#fff', padding: 24, borderRadius: 12, width: 320, maxWidth: '90%' }}>
                            <h3 style={{ marginTop: 0, color: '#b91c1c' }}>⚠️ 确认注销账号？</h3>
                            <p style={{ color: '#666', fontSize: 14 }}>
                                注销后，您的账号将无法登录，个人信息将被清空。此操作不可撤销！
                            </p>
                            <div style={{ marginBottom: 16 }}>
                                <div style={{ fontSize: 12, marginBottom: 4, color: '#333' }}>请输入密码确认：</div>
                                <input
                                    type="password"
                                    value={deletePassword}
                                    onChange={e => setDeletePassword(e.target.value)}
                                    style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }}
                                    placeholder="您的登录密码"
                                />
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                                <button
                                    onClick={() => { setShowDeleteConfirm(false); setDeletePassword(''); }}
                                    style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid #ddd', background: '#fff', cursor: 'pointer' }}
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleDeleteAccount}
                                    style={{ padding: '8px 16px', borderRadius: 6, border: 'none', background: '#dc2626', color: '#fff', cursor: 'pointer' }}
                                >
                                    确认注销
                                </button>
                            </div>
                        </div>
                    </div>
                )}

            </div>
        </div>
    );
}

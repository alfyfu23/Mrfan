"use client";

import React, { useEffect, useMemo, useState, useRef } from "react";
import { toast } from "react-toastify";
import { useUserContext } from "@/context/UserContext";
import { BACKEND_URL } from "@/constant/strings";

interface CreateGroupModalProps {
    open: boolean;
    onClose: () => void;
    onCreated?: (conversationId: number) => void;
}

export default function CreateGroupModal({ open, onClose, onCreated }: CreateGroupModalProps) {
    const { token, id_to_username, update_id_to_username, refreshConversations } = useUserContext();
    const [friends, setFriends] = useState<number[]>([]);
    const [friendActiveMap, setFriendActiveMap] = useState<Record<number, boolean | undefined>>({});
    const [selected, setSelected] = useState<number[]>([]);
    const [groupName, setGroupName] = useState("");
    const [groupAvatar, setGroupAvatar] = useState("");
    const [search, setSearch] = useState("");
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const fileRef = useRef<HTMLInputElement | null>(null);

    useEffect(() => {
        if (!open || !token) return;
        setSelected([]);
        setGroupName("");
        setGroupAvatar("");
        setSearch("");
        const fetchFriends = async () => {
            setLoading(true);
            try {
                const resp = await fetch(`https://${BACKEND_URL}/friend/list`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                const data = await resp.json();
                const list: number[] = Array.isArray(data?.friends) ? data.friends : [];
                setFriends(list);
                const activeMap: Record<number, boolean | undefined> = {};
                await Promise.all(list.map(async id => {
                    if (!token) return;
                    try {
                        const infoResp = await fetch(`https://${BACKEND_URL}/account/get_info?target=${id}`, {
                            headers: { Authorization: `Bearer ${token}` },
                        });
                        const info = await infoResp.json();
                        if (info.code === 0) {
                            const avatar = info.avatar ? (info.avatar.startsWith("/") ? `https://${BACKEND_URL}${info.avatar}` : info.avatar) : "";
                            update_id_to_username(id, { id, name: info.username, avatar, info: info.info, is_active: info.is_active });
                            activeMap[id] = info.is_active !== false;
                        }
                    } catch (err) {
                        console.error("加载用户信息失败", err);
                    }
                }));
                setFriendActiveMap(activeMap);
            } catch (err) {
                console.error("加载好友列表失败", err);
                toast.error("好友列表加载失败");
            } finally {
                setLoading(false);
            }
        };
        fetchFriends();
    }, [open, token, update_id_to_username]);

    const friendItems = useMemo(() => {
        const keyword = search.trim().toLowerCase();
        return friends
            .map(id => {
                const info = id_to_username[id];
                const name = info?.name ?? `用户#${id}`;
                return { id, name };
            })
            .filter(item => {
                const active = friendActiveMap[item.id];
                if (active === false) return false;
                const cached = id_to_username[item.id]?.is_active;
                return cached !== false;
            })
            .filter(item => !keyword || item.name.toLowerCase().includes(keyword));
    }, [friends, id_to_username, friendActiveMap, search]);

    const toggleSelect = (id: number) => {
        setSelected(prev => (prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]));
    };

    const canSubmit = groupName.trim().length > 0 && selected.length >= 1 && !submitting;

    const handleSubmit = async () => {
        if (!token || !canSubmit) return;
        setSubmitting(true);
        try {
            const resp = await fetch(`https://${BACKEND_URL}/chat/group/create`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    name: groupName.trim(),
                    members: selected,
                    avatar: groupAvatar
                }),
            });
            const data = await resp.json();
            if (data.code !== 0) {
                toast.error(data.info || "创建群聊失败");
                return;
            }
            toast.success("群聊创建成功");
            await refreshConversations();
            onCreated?.(data.id);
            onClose();
        } catch (err) {
            console.error("创建群聊异常", err);
            toast.error("创建群聊失败，请稍后再试");
        } finally {
            setSubmitting(false);
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
            setGroupAvatar(url);
        } catch (err) {
            console.error(err);
            toast.error('上传异常');
        } finally {
            if (fileRef.current) fileRef.current.value = '';
        }
    };

    if (!open) return null;

    return (
        <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.45)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
            <div onClick={e => e.stopPropagation()} style={{ width: "min(420px, 100%)", background: "#fff", borderRadius: 16, padding: 24, boxShadow: "0 20px 60px rgba(15,23,42,0.25)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                    <div style={{ fontSize: 18, fontWeight: 600 }}>发起群聊</div>
                    <button type="button" onClick={onClose} style={{ border: "none", background: "transparent", cursor: "pointer", fontSize: 20 }}>×</button>
                </div>
                
                {/* 群头像 */}
                <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
                    <div style={{ width: 60, height: 60, borderRadius: 12, overflow: "hidden", background: "#f3f4f6", display: "grid", placeItems: "center" }}>
                        {groupAvatar ? <img src={groupAvatar} alt="群头像" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : <span style={{ color: "#9ca3af" }}>群头像</span>}
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
                        <div style={{ fontSize: 14, color: "#6b7280" }}>群头像（可选）</div>
                        <div style={{ display: "flex", gap: 8 }}>
                            <input
                                value={groupAvatar}
                                onChange={e => setGroupAvatar(e.target.value)}
                                placeholder="图片URL"
                                style={{
                                    flex: 1,
                                    border: "1px solid #d7dbe7",
                                    borderRadius: 8,
                                    padding: "6px 10px",
                                    fontSize: 13
                                }}
                            />
                            <label style={{
                                padding: "6px 12px",
                                borderRadius: 8,
                                background: "#f3f4f6",
                                border: "1px solid #d7dbe7",
                                color: "#374151",
                                cursor: "pointer",
                                fontSize: 13
                            }}>
                                上传
                                <input
                                    ref={fileRef}
                                    type="file"
                                    accept="image/*"
                                    style={{ display: "none" }}
                                    onChange={handleAvatarUpload}
                                />
                            </label>
                        </div>
                    </div>
                </div>
                
                <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 14 }}>
                    群名称
                    <input
                        value={groupName}
                        onChange={e => setGroupName(e.target.value)}
                        placeholder="请输入群聊名称"
                        style={{ border: "1px solid #d7dbe7", borderRadius: 10, padding: "10px 12px", fontSize: 14 }}
                    />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 14, marginTop: 16 }}>
                    邀请好友
                    <input
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        placeholder="搜索好友"
                        style={{ border: "1px solid #e2e8f0", borderRadius: 10, padding: "8px 10px", fontSize: 13 }}
                    />
                </label>
                <div style={{ marginTop: 12, maxHeight: 240, overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: 12, padding: 8 }}>
                    {loading && <div style={{ padding: 12, textAlign: "center", color: "#64748b" }}>正在加载好友…</div>}
                    {!loading && friendItems.length === 0 && <div style={{ padding: 12, textAlign: "center", color: "#94a3b8" }}>暂无可选好友</div>}
                    {!loading && friendItems.map(item => (
                        <label key={item.id} style={{ display: "flex", alignItems: "center", padding: "6px 4px", borderRadius: 8, cursor: "pointer", gap: 8 }}>
                            <input
                                type="checkbox"
                                checked={selected.includes(item.id)}
                                onChange={() => toggleSelect(item.id)}
                                style={{ width: 16, height: 16 }}
                            />
                            <span>{item.name}</span>
                        </label>
                    ))}
                </div>
                <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end", gap: 12 }}>
                    <button type="button" onClick={onClose} style={{ padding: "10px 16px", borderRadius: 10, border: "1px solid #e2e8f0", background: "#fff", cursor: "pointer" }}>取消</button>
                    <button
                        type="button"
                        onClick={handleSubmit}
                        disabled={!canSubmit}
                        style={{
                            padding: "10px 20px",
                            borderRadius: 10,
                            border: "none",
                            background: canSubmit ? "#4f46e5" : "#cbd5f5",
                            color: "#fff",
                            cursor: canSubmit ? "pointer" : "not-allowed",
                            minWidth: 100,
                        }}
                    >
                        {submitting ? "创建中…" : "创建"}
                    </button>
                </div>
            </div>
        </div>
    );
}

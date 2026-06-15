"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { BACKEND_URL } from "@/constant/strings";
import { useUserContext } from "@/context/UserContext";
import { User } from "@/types/User";
import SearchBar, { SearchBarActionKey } from "./SearchBar";

interface SocialPanelProps {
    onGroupCreated?: (conversationId: number) => void;
}

export default function SocialPanel({ onGroupCreated }: SocialPanelProps) {
    const { token, id_to_username, update_id_to_username, selfId } = useUserContext();
    const [friends, setFriends] = useState<number[]>([]);
    const [pendings, setPendings] = useState<number[]>([]);
    const [groups, setGroups] = useState<{ id: number; name: string; members: number[] }[]>([]);
    const [collapsed, setCollapsed] = useState<Record<number, boolean>>({});
    const [addingToGroup, setAddingToGroup] = useState<Record<number, number | null | undefined>>({});
    const [query, setQuery] = useState("");
    const [searchExact, setSearchExact] = useState<number[]>([]);
    const [searchFuzzy, setSearchFuzzy] = useState<number[]>([]);
    const searchInputRef = useRef<HTMLInputElement>(null);

    const idMapRef = useRef(id_to_username);

    useEffect(() => {
        idMapRef.current = id_to_username;
    }, [id_to_username]);

    const loadUserBasic = useCallback(async (id: number, force = false) => {
        if (!token) return;
        if (!force && idMapRef.current[id]) return;
        try {
            const r = await fetch(`https://${BACKEND_URL}/account/get_info?target=${id}`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await r.json();
            if (data.code === 0) {
                const ava = (data.avatar || '') as string;
                const norm = ava && ava.startsWith('/') ? `https://${BACKEND_URL}${ava}` : ava;
                const u: User = { 
                    id, 
                    name: data.username, 
                    avatar: norm, 
                    info: data.info,
                    is_active: data.is_active
                };
                update_id_to_username(id, u);
            }
        } catch (err) {
            console.error('加载用户信息失败:', err);
        }
    }, [token, update_id_to_username]);

    const fetchList = useCallback(async () => {
        if (!token) return;
        try {
            const r = await fetch(`https://${BACKEND_URL}/friend/list`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await r.json();
            setFriends(data.friends || []);
            setPendings(data.pending || []);
            // 预取基本信息
            [...(data.friends || []), ...(data.pending || [])].forEach((fid) => loadUserBasic(fid, true));
        } catch (err) {
            console.error('加载好友列表失败:', err);
        }
    }, [token, loadUserBasic]);

    const fetchGroups = useCallback(async () => {
        if (!token) return;
        try {
            const r = await fetch(`https://${BACKEND_URL}/friend/group/list`, { headers: { Authorization: `Bearer ${token}` } });
            const data = await r.json();
            if (data && data.code === 0) {
                    // 后端会把未分组作为 id=0 返回，但前端不应把它当作普通分组展示
                    const allGroups: { id: number; name: string; members: number[] }[] = data.groups || [];
                    const normalGroups = allGroups.filter(g => g.id !== 0);
                    setGroups(normalGroups);
                    normalGroups.forEach((g) => (g.members || []).forEach((mid) => loadUserBasic(mid)));
                }
        } catch (err) {
            console.error('加载分组失败:', err);
        }
    }, [token, loadUserBasic]);

    useEffect(() => {
        const map: Record<number, boolean> = {};
        groups.forEach(g => { map[g.id] = map[g.id] ?? false; });
        setCollapsed(prev => ({ ...map, ...prev }));
    }, [groups]);

    // Create group
    async function createGroup() {
        if (!token) return;
        const name = window.prompt('请输入新分组名称：', '新分组');
        if (!name) return;
        try {
            const r = await fetch(`https://${BACKEND_URL}/friend/group/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ name })
            });
            const d = await r.json();
            if (d.code === 0) {
                await fetchGroups();
            } else {
                alert(d.info || '创建分组失败');
            }
        } catch (err) {
            console.error('创建分组错误', err);
            alert('创建分组失败');
        }
    }

    const toggleGroup = (groupId: number) => setCollapsed(prev => ({ ...prev, [groupId]: !prev[groupId] }));

    // Compute ungrouped friends
    const groupedIds = new Set<number>();
    groups.forEach(g => (g.members || []).forEach(id => groupedIds.add(id)));
    const ungrouped = friends.filter(id => !groupedIds.has(id));

    const handleAddToGroup = (groupId: number) => {
        setAddingToGroup(prev => ({ ...prev, [groupId]: prev[groupId] ?? (ungrouped[0] || null) }));
    };

    const confirmAddToGroup = async (groupId: number) => {
        const friendId = addingToGroup[groupId];
        if (!friendId) return alert('请先选择好友');
        try {
            const r = await fetch(`https://${BACKEND_URL}/friend/group/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ group_id: groupId, friend_id: friendId })
            });
            const d = await r.json();
            if (d.code === 0) {
                await fetchGroups();
                await fetchList();
                setAddingToGroup(prev => ({ ...prev, [groupId]: null }));
            } else {
                alert(d.info || '添加失败');
            }
        } catch (err) {
            console.error('添加分组成员异常', err);
            alert('添加失败');
        }
    };

    const handleRemoveFromGroup = async (groupId: number, friendId: number) => {
        try {
            const r = await fetch(`https://${BACKEND_URL}/friend/group/remove`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ group_id: groupId, friend_id: friendId })
            });
            const d = await r.json();
            if (d.code === 0) {
                await fetchGroups();
            } else {
                alert(d.info || '移除失败');
            }
        } catch (err) {
            console.error('移除分组成员异常', err);
            alert('移除失败');
        }
    };

    const handleRenameGroup = async (groupId: number) => {
        const name = window.prompt('请输入新的分组名称：');
        if (!name) return;
        try {
            const r = await fetch(`https://${BACKEND_URL}/friend/group/rename`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ group_id: groupId, name })
            });
            const d = await r.json();
            if (d.code === 0) {
                await fetchGroups();
            } else {
                alert(d.info || '重命名失败');
            }
        } catch (err) {
            console.error('重命名异常', err);
            alert('重命名失败');
        }
    };

    const handleDeleteGroup = async (groupId: number) => {
        if (!window.confirm('确认删除该分组？成员会被移到未分组')) return;
        try {
            const r = await fetch(`https://${BACKEND_URL}/friend/group/delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ group_id: groupId })
            });
            const d = await r.json();
            if (d.code === 0) {
                await fetchGroups();
            } else {
                alert(d.info || '删除失败');
            }
        } catch (err) {
            console.error('删除分组异常', err);
            alert('删除失败');
        }
    };

    async function doSearch() {
        if (!token || !query.trim()) { setSearchExact([]); setSearchFuzzy([]); return; }
        try {
            const r = await fetch(`https://${BACKEND_URL}/friend/search/${encodeURIComponent(query)}`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await r.json();
            setSearchExact(data.exact || []);
            setSearchFuzzy(data.fuzzy || []);
            [...(data.exact || []), ...(data.fuzzy || [])].forEach((sid) => loadUserBasic(sid));
        } catch (err) {
            console.error('搜索失败:', err);
        }
    }

    async function addFriend(id: number) {
        if (!token) return;
        // 检查是否尝试添加自己为好友
        if (id === selfId) {
            alert('不能添加自己为好友');
            return;
        }
        try {
            await fetch(`https://${BACKEND_URL}/friend/add/${id}`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
            });
            fetchList();
        } catch (err) {
            console.error('发送好友请求失败:', err);
        }
    }

    async function agree(id: number) {
        if (!token) return;
        try {
            // 乐观更新，假设同意好友后会立即更新UI
            setPendings(prev => prev.filter(x => x !== id));  // 从待处理列表中移除
            setFriends(prev => prev.includes(id) ? prev : [...prev, id]);  // 加入好友列表

            // 发送请求同意好友
            const response = await fetch(`https://${BACKEND_URL}/friend/agree/${id}`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                }
            });

            // 如果同意好友成功，则创建好友会话
            if (response.ok) {
                // 发送请求创建好友会话
                const chatResponse = await fetch(`https://${BACKEND_URL}/chat/create/friend`, {
                    method: 'POST',
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ id }),  // 发送对方ID来创建会话
                });

                // 如果创建好友会话成功，处理响应
                if (chatResponse.ok) {
                    await chatResponse.json();
                } else {
                    const chatError = await chatResponse.json();
                    console.error('创建好友会话失败:', chatError);
                }
            } else {
                const errorData = await response.json();
                console.error('同意好友失败:', errorData);
            }

            // 刷新好友列表
            fetchList();

        } catch (err) {
            console.error('处理好友申请失败:', err);
        }
    }


    async function disagree(id: number) {
        if (!token) return;
        try {
            setPendings(prev => prev.filter(x => x !== id));
            await fetch(`https://${BACKEND_URL}/friend/disagree/${id}`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
            fetchList();
        } catch (err) {
            console.error('拒绝好友失败:', err);
        }
    }

    async function removeFriend(id: number) {
        if (!token) return;
        try {
            setFriends(prev => prev.filter(x => x !== id));
            await fetch(`https://${BACKEND_URL}/friend/delete/${id}`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
            fetchList();
        } catch (err) {
            console.error('删除好友失败:', err);
        }
    }

    useEffect(() => {
        let mounted = true;
        (async () => {
            try {
                if (!mounted) return;
                await fetchList();
                await fetchGroups();
            } catch {}
        })();
        return () => { mounted = false; };
    }, [fetchList, fetchGroups]);

    const defaultAvatarUrl = `https://${BACKEND_URL}/asset/default.png`;

    const handleQuickAction = (action: SearchBarActionKey) => {
        if (action === 'add-friend') {
            searchInputRef.current?.focus();
            searchInputRef.current?.select();
        } else if (action === 'add-friend-group') {
            void createGroup();
        }
    };

    const renderUser = (id: number, action?: React.ReactNode) => {
        const u = id_to_username[id];
        return (
            <div key={id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', borderBottom: '1px solid #eee' }}>
                <div style={{ width: 28, height: 28, borderRadius: '50%', background: '#ccc', overflow: 'hidden' }}>
                    <img src={u?.avatar || defaultAvatarUrl} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                </div>
                <div style={{ flex: 1 }}>
                    {u?.name ?? `用户#${id}`}
                    {u?.is_active === false && <span style={{ color: 'red', fontSize: '0.8em', marginLeft: '4px' }}>(已注销)</span>}
                </div>
                {action}
            </div>
        );
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{ padding: 12, borderBottom: '1px solid #e0e0e0' }}>
                <SearchBar
                    value={query}
                    onChange={setQuery}
                    onSearch={doSearch}
                    placeholder="搜索用户名…"
                    inputRef={searchInputRef}
                    onGroupCreated={onGroupCreated}
                    onActionSelect={handleQuickAction}
                    actions={[{ key: "add-friend-group", label: "好友分组" }]}
                />
            </div>
            {/* 搜索结果 */}
            <div style={{ padding: 8 }}>
                {searchExact.length > 0 && (
                    <div>
                        <div style={{ fontWeight: 600, margin: '8px 0' }}>精确匹配</div>
                        {searchExact.map(id => {
                            const isFriend = friends.includes(id);
                            const isPending = pendings.includes(id);
                            const showAddButton = id !== selfId && !isFriend && !isPending;
                            return renderUser(id, showAddButton ? <button type="button" onClick={() => addFriend(id)}>加好友</button> : null);
                        })}
                    </div>
                )}
                {searchFuzzy.length > 0 && (
                    <div>
                        <div style={{ fontWeight: 600, margin: '8px 0' }}>模糊匹配</div>
                        {searchFuzzy.map(id => {
                            const isFriend = friends.includes(id);
                            const isPending = pendings.includes(id);
                            const showAddButton = id !== selfId && !isFriend && !isPending;
                            return renderUser(id, showAddButton ? <button type="button" onClick={() => addFriend(id)}>加好友</button> : null);
                        })}
                    </div>
                )}
            </div>
            {/* 待处理 */}
            <div style={{ padding: 8 }}>
                <div style={{ fontWeight: 600, margin: '8px 0' }}>待处理好友申请</div>
                {pendings.length === 0 && <div style={{ color: '#888' }}>暂无</div>}
                {pendings.map(id => renderUser(id, (
                    <div style={{ display: 'flex', gap: 6 }}>
                        <button type="button" onClick={() => agree(id)}>同意</button>
                        <button type="button" onClick={() => disagree(id)}>拒绝</button>
                    </div>
                )))}
            </div>
            {/* 好友列表（按分组显示） */}
            <div style={{ padding: 8, overflowY: 'auto' }}>
                <div style={{ fontWeight: 600, margin: '8px 0' }}>我的好友</div>
                {groups.length === 0 && friends.length === 0 && <div style={{ color: '#888' }}>暂无好友</div>}

                {groups.map(g => (
                    <div key={g.id} style={{ marginBottom: 12, border: '1px solid #f3f4f6', borderRadius: 8, overflow: 'hidden' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', background: '#fafafa' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <button onClick={() => toggleGroup(g.id)} style={{ border: 'none', background: 'transparent', cursor: 'pointer' }}>{collapsed[g.id] ? '▸' : '▾'}</button>
                                <div style={{ fontWeight: 600 }}>{g.name}</div>
                                <div style={{ color: '#888', fontSize: 12, marginLeft: 8 }}>{(g.members || []).length} 人</div>
                            </div>
                            <div style={{ display: 'flex', gap: 8 }}>
                                {/* 系统生成的未分组（id===0）不应有分组管理操作 */}
                                {g.id !== 0 ? (
                                    <>
                                        <button onClick={() => handleAddToGroup(g.id)} style={{ padding: '6px 8px' }}>添加成员</button>
                                        <button onClick={() => handleRenameGroup(g.id)} style={{ padding: '6px 8px' }}>重命名</button>
                                        <button onClick={() => handleDeleteGroup(g.id)} style={{ padding: '6px 8px', color: '#b91c1c' }}>删除分组</button>
                                    </>
                                ) : (
                                    <div style={{ color: '#888', fontSize: 12, padding: '6px 8px' }}>系统分组</div>
                                )}
                            </div>
                        </div>
                        {!collapsed[g.id] && (
                            <div>
                                {(g.members || []).length === 0 && <div style={{ padding: 8, color: '#888' }}>空</div>}
                                {(g.members || []).map(id => (
                                    <div key={id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        {renderUser(id)}
                                        <div style={{ display: 'flex', gap: 8, paddingRight: 8 }}>
                                            <button onClick={() => handleRemoveFromGroup(g.id, id)} style={{ padding: '6px 8px' }}>移出分组</button>
                                            <button onClick={() => removeFriend(id)} style={{ padding: '6px 8px', color: '#b91c1c' }}>删除好友</button>
                                        </div>
                                    </div>
                                ))}
                                {/* 添加成员内嵌选择（仅普通分组可添加） */}
                                {g.id !== 0 && Object.prototype.hasOwnProperty.call(addingToGroup, g.id) && (
                                    <div style={{ padding: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
                                        {ungrouped.length === 0 ? <div style={{ color: '#888' }}>没有可添加的未分组好友</div> : (
                                            <>
                                                <select value={addingToGroup[g.id] ?? ''} onChange={e => setAddingToGroup(prev => ({ ...prev, [g.id]: Number(e.target.value) }))}>
                                                    <option value="">请选择好友</option>
                                                    {ungrouped.map(id => <option key={id} value={id}>{id_to_username[id]?.name ?? `用户#${id}`}</option>)}
                                                </select>
                                                <button onClick={() => confirmAddToGroup(g.id)} style={{ padding: '6px 8px' }}>确认添加</button>
                                                <button onClick={() => setAddingToGroup(prev => { const cp = { ...prev }; delete cp[g.id]; return cp; })} style={{ padding: '6px 8px' }}>取消</button>
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}

                {/* 未分组 */}
                <div style={{ marginTop: 8 }}>
                    <div style={{ fontWeight: 600, margin: '6px 0' }}>未分组</div>
                    {ungrouped.length === 0 && <div style={{ color: '#888' }}>暂无</div>}
                    {(ungrouped || []).map(id => (
                        <div key={id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            {renderUser(id)}
                            <div style={{ display: 'flex', gap: 8, paddingRight: 8 }}>
                                {/* 未分组区仅允许删除好友 */}
                                <button onClick={() => removeFriend(id)} style={{ padding: '6px 8px', color: '#b91c1c' }}>删除好友</button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

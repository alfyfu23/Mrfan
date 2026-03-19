"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import type { StaticImageData } from "next/image";
import searchIcon from "../../asset/search.png";
import plusIcon from "../../asset/new.png";
import CreateGroupModal from "./CreateGroupModal";

export type SearchBarActionKey = "add-friend" | "start-group" | "add-friend-group" | string;

export interface SearchBarAction {
    key: SearchBarActionKey;
    label: string;
    onClick?: () => void;
}

interface SearchBarProps {
    value: string;
    placeholder?: string;
    onChange: (value: string) => void;
    onSearch?: () => void;
    actions?: SearchBarAction[];
    onActionSelect?: (action: SearchBarActionKey) => void;
    inputRef?: React.RefObject<HTMLInputElement | null>;
    style?: React.CSSProperties;
    onGroupCreated?: (conversationId: number) => void;
}

const defaultActions: SearchBarAction[] = [
    { key: "add-friend", label: "添加好友" },
    { key: "start-group", label: "发起群聊" },
];

export default function SearchBar({
    value,
    placeholder = "搜索...",
    onChange,
    onSearch,
    actions,
    onActionSelect,
    inputRef,
    style,
    onGroupCreated,
}: SearchBarProps) {
    const [open, setOpen] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const containerRef = useRef<HTMLDivElement | null>(null);
    const internalInputRef = useRef<HTMLInputElement | null>(null);
    const mergedInputRef = useMemo(() => inputRef ?? internalInputRef, [inputRef]);

    useEffect(() => {
        if (!open) return;
        const handleClickOutside = (event: MouseEvent) => {
            if (!containerRef.current) return;
            if (!containerRef.current.contains(event.target as Node)) {
                setOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [open]);

    // 如果没有明确提供 actions，则不显示 action-menu-button
    const finalActions = actions || [];

    const handleSearch = () => {
        onSearch?.();
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
        if (event.key === "Enter") {
            event.preventDefault();
            handleSearch();
        }
    };

    const handleActionClick = (action: SearchBarAction) => {
        if (action.key === "start-group") {
            setShowCreateModal(true);
        }
        // "add-friend-group" action will be handled by the onActionSelect callback
        action.onClick?.();
        onActionSelect?.(action.key);
        setOpen(false);
    };

    return (
        <>
            <div className="search-bar-container" ref={containerRef} style={style}>
                <div className="search-input-wrapper">
                    <input
                        ref={mergedInputRef}
                        type="text"
                        value={value}
                        onChange={e => onChange(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={placeholder}
                        className="search-input"
                    />
                    <button type="button" onClick={handleSearch} className="search-button">
                        <Image src={searchIcon as StaticImageData} alt="搜索" width={18} height={18} />
                    </button>
                </div>
                <div className="action-menu-container">
                    <button type="button" onClick={() => setOpen(prev => !prev)} className="action-menu-button">
                        <Image src={plusIcon as StaticImageData} alt="快捷操作" width={20} height={20} />
                    </button>
                    {open && (
                        <div className="action-menu-dropdown">
                            {finalActions.map(action => (
                                <button
                                    key={action.key}
                                    type="button"
                                    onClick={() => handleActionClick(action)}
                                    className="action-menu-item"
                                >
                                    {action.label}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
            <CreateGroupModal open={showCreateModal} onClose={() => setShowCreateModal(false)} onCreated={onGroupCreated} />

            <style jsx>{`
                .search-bar-container {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    width: 100%;
                    min-width: 0; /* 确保容器可以收缩 */
                }

                .search-input-wrapper {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px 16px;
                    border: 1px solid rgba(102, 126, 234, 0.2);
                    border-radius: 24px;
                    background: rgba(255, 255, 255, 0.8);
                    backdrop-filter: blur(10px);
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
                    transition: all 0.3s ease;
                    min-width: 0; /* 允许输入框收缩 */
                    overflow: hidden; /* 防止内容溢出 */
                }

                .search-input-wrapper:focus-within {
                    border-color: #667eea;
                    background: rgba(255, 255, 255, 0.95);
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }

                .search-input {
                    flex: 1;
                    border: none;
                    outline: none;
                    font-size: 15px;
                    background: transparent;
                    color: #333;
                    min-width: 0;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }

                .search-input::placeholder {
                    color: #999;
                }

                .search-button {
                    width: 32px;
                    height: 32px;
                    min-width: 32px;
                    max-width: 32px;
                    flex-shrink: 0;
                    border-radius: 50%;
                    border: none;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: grid;
                    place-items: center;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    box-shadow: 0 2px 6px rgba(102, 126, 234, 0.2);
                }

                .search-button:hover {
                    transform: scale(1.05);
                    box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
                }

                .action-menu-container {
                    position: relative;
                    z-index: 100;
                    display: ${finalActions && finalActions.length > 0 ? 'block' : 'none'};
                }

                .action-menu-button {
                    width: 40px;
                    height: 40px;
                    border-radius: 12px;
                    border: 1px solid rgba(102, 126, 234, 0.2);
                    background: rgba(255, 255, 255, 0.8);
                    display: grid;
                    place-items: center;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
                }

                .action-menu-button:hover {
                    background: rgba(102, 126, 234, 0.1);
                    transform: translateY(-2px);
                }

                .action-menu-dropdown {
                    position: absolute;
                    right: 0;
                    top: calc(100% + 8px);
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(102, 126, 234, 0.2);
                    border-radius: 12px;
                    padding: 8px;
                    min-width: 140px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                    z-index: 1000;
                }

                .action-menu-item {
                    width: 100%;
                    text-align: left;
                    padding: 10px 14px;
                    border-radius: 8px;
                    border: none;
                    background: transparent;
                    cursor: pointer;
                    font-size: 14px;
                    color: #333;
                    transition: all 0.2s ease;
                }

                .action-menu-item:hover {
                    background: rgba(102, 126, 234, 0.1);
                    color: #667eea;
                }
            `}</style>
        </>
    );
}
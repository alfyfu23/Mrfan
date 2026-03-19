import React, { useState } from 'react';
import { BACKEND_URL } from '@/constant/strings';

interface AvatarProps {
    src?: string;
    alt?: string;
    size?: number | string;
    className?: string;
    style?: React.CSSProperties;
    fallbackText?: string;
    onClick?: () => void;
    title?: string;
}

export default function Avatar({ 
    src, 
    alt = 'avatar', 
    size = 40, 
    className = '', 
    style = {}, 
    fallbackText,
    onClick,
    title
}: AvatarProps) {
    const [imgSrc, setImgSrc] = useState<string | null>(() => {
        if (!src) return null;
        // 处理相对路径
        return src.startsWith('/') ? `https://${BACKEND_URL}${src}` : src;
    });
    const [hasError, setHasError] = useState(false);

    const handleError = () => {
        if (!hasError) {
            setHasError(true);
            // 触发回退到文本占位
            setImgSrc(null);
        }
    };

    const containerStyle: React.CSSProperties = {
        width: typeof size === 'number' ? `${size}px` : size,
        height: typeof size === 'number' ? `${size}px` : size,
        borderRadius: '50%',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f0f0f0',
        ...style
    };

    // 如果没有图片源，显示fallback文本
    if (!imgSrc) {
        return (
            <div 
                className={`avatar-fallback ${className}`}
                style={containerStyle}
                onClick={onClick}
                title={title}
            >
                <span style={{ 
                    fontSize: typeof size === 'number' ? `${size * 0.4}px` : '16px',
                    color: '#000',
                    fontWeight: 'bold'
                }}>
                    {fallbackText || (alt ? alt.charAt(0).toUpperCase() : '?')}
                </span>
            </div>
        );
    }

    return (
        <div 
            className={`avatar-container ${className}`}
            style={containerStyle}
            onClick={onClick}
            title={title}
        >
            <img
                src={imgSrc}
                alt={alt}
                onError={handleError}
                style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    display: 'block'
                }}
            />
        </div>
    );
}
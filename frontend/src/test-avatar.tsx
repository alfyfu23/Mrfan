"use client";

import React from 'react';
import Avatar from './components/Avatar';

export default function TestAvatarPage() {
  return (
    <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h1>头像加载测试</h1>
      
      <div>
        <h2>正常头像</h2>
        <Avatar src="/asset/default_user.jpg" size={60} alt="正常头像" />
      </div>
      
      <div>
        <h2>不存在的头像（应显示默认头像）</h2>
        <Avatar src="/asset/nonexistent.jpg" size={60} alt="不存在的头像" fallbackText="N" />
      </div>
      
      <div>
        <h2>无效URL（应显示默认头像）</h2>
        <Avatar src="https://invalid-url-that-does-not-exist.com/avatar.jpg" size={60} alt="无效URL" fallbackText="I" />
      </div>
      
      <div>
        <h2>无头像（应显示fallback文本）</h2>
        <Avatar size={60} alt="无头像" fallbackText="U" />
      </div>
      
      <div>
        <h2>网络错误（应显示默认头像）</h2>
        <Avatar src="https://httpstat.us/404.jpg" size={60} alt="网络错误" fallbackText="E" />
      </div>
    </div>
  );
}
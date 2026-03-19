'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUserContext } from '@/context/UserContext';
import MainPage from '@/components/MainPage';

export default function Home() {
    const { token, isInitialized } = useUserContext();
    const isLoggedIn = token != null;
    
    console.log(token, isLoggedIn, isInitialized);
    const router = useRouter();

    useEffect(() => {
        // 只有在初始化完成后才进行登录状态检查
        if (isInitialized && !isLoggedIn) {
            router.push('/login');
        }
    }, [isInitialized, isLoggedIn, router]);

    // 如果还未初始化，显示加载状态
    if (!isInitialized) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                fontSize: '18px'
            }}>
                正在检查登录状态...
            </div>
        );
    }

    // 如果已初始化但未登录，不渲染任何内容（等待跳转）
    if (!isLoggedIn) {
        return null;
    }

    return <MainPage />;
}

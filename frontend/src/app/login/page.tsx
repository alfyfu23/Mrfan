'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUserContext } from '@/context/UserContext';
import { validatePasswordStrength, getPasswordStrengthDescription, getPasswordStrengthColor, PasswordValidationResult } from '@/utils/passwordValidator';
import { validateUsername, getUsernameRequirements, UsernameValidationResult } from '@/utils/usernameValidator';
import { toast } from 'react-toastify';
import { BACKEND_URL } from '@/constant/strings';

export default function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [isLogin, setIsLogin] = useState(true); // 登录/注册切换
    const [passwordValidation, setPasswordValidation] = useState<PasswordValidationResult | null>(null);
    const [usernameValidation, setUsernameValidation] = useState<UsernameValidationResult | null>(null);
    const [showUsernameRequirements, setShowUsernameRequirements] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [autoRegisterData, setAutoRegisterData] = useState<{ username: string; password: string } | null>(null);
    
    const { login, register, token, isInitialized } = useUserContext();
    const isLoggedIn = (token != null);
    const router = useRouter();

    useEffect(() => {
        // 只有在初始化完成后且已登录时才跳转
        if (isInitialized && isLoggedIn) {
            router.push('/');
        }
    }, [isInitialized, isLoggedIn, router]);

    // 密码变化时验证强度
    useEffect(() => {
        if (password && !isLogin) {
            const validation = validatePasswordStrength(password);
            setPasswordValidation(validation);
        } else {
            setPasswordValidation(null);
        }
    }, [password, isLogin]);

    // 用户名变化时验证格式
    useEffect(() => {
        if (username && !isLogin) {
            const validation = validateUsername(username);
            setUsernameValidation(validation);
        } else {
            setUsernameValidation(null);
        }
    }, [username, isLogin]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            if (isLogin) {
                // 登录逻辑
                const loginResult = await login(username, password);
                
                // 如果用户不存在，自动跳转到注册界面并预填信息
                if (loginResult.needsRegister) {
                    toast.info('用户不存在，将跳转到注册页面');
                    setAutoRegisterData({ username, password });
                    setIsLogin(false);
                    setIsLoading(false);
                    return;
                }
                
                // 如果登录有其他错误，显示错误信息
                if (loginResult.error) {
                    toast.error(loginResult.error);
                    setIsLoading(false);
                    return;
                }
            } else {
                // 注册逻辑
                if (password !== confirmPassword) {
                    toast.error('两次输入的密码不一致');
                    setIsLoading(false);
                    return;
                }

                const usernameValidationResult = validateUsername(username);
                if (!usernameValidationResult.isValid) {
                    toast.error('用户名不符合要求：' + usernameValidationResult.errors.join('，'));
                    setIsLoading(false);
                    return;
                }

                const validation = validatePasswordStrength(password);
                if (!validation.isValid) {
                    toast.error('密码不符合要求：' + validation.errors.join('，'));
                    setIsLoading(false);
                    return;
                }

                // 使用UserContext中的register函数
                const registerSuccess = await register(username, password);
                
                if (registerSuccess) {
                    // 注册成功后自动登录
                    toast.success('注册成功！正在登录...');
                    const loginResult = await login(username, password);
                    if (loginResult.error) {
                        toast.error(loginResult.error);
                    }
                }
            }
        } catch (error) {
            console.error('操作失败:', error);
            toast.error('操作失败，请稍后再试');
        } finally {
            setIsLoading(false);
        }
    };

    const toggleMode = () => {
        setIsLogin(!isLogin);
        // 如果是从登录跳转到注册，且没有自动注册数据，则清空表单
        if (!autoRegisterData) {
            setPassword('');
            setConfirmPassword('');
            setUsernameValidation(null);
        }
        setPasswordValidation(null);
        setShowUsernameRequirements(false);
        setAutoRegisterData(null);
    };
    
    // 当自动注册数据变化时，更新表单
    useEffect(() => {
        if (autoRegisterData) {
            setUsername(autoRegisterData.username);
            setPassword(autoRegisterData.password);
            // 自动填充确认密码
            setConfirmPassword(autoRegisterData.password);
            // 验证用户名和密码
            const usernameValidationResult = validateUsername(autoRegisterData.username);
            setUsernameValidation(usernameValidationResult);
            const passwordValidationResult = validatePasswordStrength(autoRegisterData.password);
            setPasswordValidation(passwordValidationResult);
        }
    }, [autoRegisterData]);

    // 如果正在初始化，显示加载页面
    if (!isInitialized) {
        return (
            <div className="loading-container">
                <div className="loading-spinner"></div>
                <style jsx>{`
                    .loading-container {
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }
                    .loading-spinner {
                        width: 40px;
                        height: 40px;
                        border: 4px solid rgba(255, 255, 255, 0.3);
                        border-radius: 50%;
                        border-top-color: white;
                        animation: spin 1s ease-in-out infinite;
                    }
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                `}</style>
            </div>
        );
    }

    return (
        <div className="login-container">
            <div className="login-form-container">
                <div className="login-header">
                    <h1 className="login-title">{isLogin ? '欢迎回来' : '创建账号'}</h1>
                    <p className="login-subtitle">
                        {isLogin ? '登录您的即时通讯账号' : '注册新的即时通讯账号'}
                    </p>
                    {autoRegisterData && !isLogin && (
                        <div className="auto-register-notice">
                            <p>已为您预填用户名和密码，请检查信息后完成注册</p>
                        </div>
                    )}
                </div>

                <form onSubmit={handleSubmit} className="login-form">
                    <div className="form-group">
                        <label htmlFor="username" className="form-label">用户名</label>
                        <input
                            type="text"
                            id="username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            className="form-input"
                            placeholder="请输入用户名"
                            onFocus={() => !isLogin && setShowUsernameRequirements(true)}
                            onBlur={() => setShowUsernameRequirements(false)}
                        />
                        {!isLogin && showUsernameRequirements && (
                            <div className="username-requirements">
                                <div className="requirements-title">用户名格式要求：</div>
                                {getUsernameRequirements().map((requirement, index) => (
                                    <div key={index} className="requirement-item">
                                        • {requirement}
                                    </div>
                                ))}
                            </div>
                        )}
                        {!isLogin && usernameValidation && usernameValidation.errors.length > 0 && (
                            <div className="username-errors">
                                {usernameValidation.errors.map((error, index) => (
                                    <div key={index} className="username-error">
                                        • {error}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="form-group">
                        <label htmlFor="password" className="form-label">密码</label>
                        <div className="password-input-container">
                            <input
                                type={showPassword ? "text" : "password"}
                                id="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                className="form-input"
                                placeholder="请输入密码"
                            />
                            <button
                                type="button"
                                className="password-toggle"
                                onClick={() => setShowPassword(!showPassword)}
                            >
                                {showPassword ? '隐藏' : '显示'}
                            </button>
                        </div>
                    </div>

                    {!isLogin && (
                        <>
                            <div className="form-group">
                                <label htmlFor="confirmPassword" className="form-label">确认密码</label>
                                <div className="password-input-container">
                                    <input
                                        type={showConfirmPassword ? "text" : "password"}
                                        id="confirmPassword"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        required
                                        className="form-input"
                                        placeholder="请再次输入密码"
                                    />
                                    <button
                                        type="button"
                                        className="password-toggle"
                                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    >
                                        {showConfirmPassword ? '隐藏' : '显示'}
                                    </button>
                                </div>
                            </div>

                            {passwordValidation && (
                                <div className="password-strength-container">
                                    <div className="password-strength-header">
                                        <span>密码强度：</span>
                                        <span 
                                            className="password-strength-text"
                                            style={{ color: getPasswordStrengthColor(passwordValidation.strength) }}
                                        >
                                            {getPasswordStrengthDescription(passwordValidation.strength)}
                                        </span>
                                    </div>
                                    <div className="password-strength-bar">
                                        <div 
                                            className="password-strength-fill"
                                            style={{ 
                                                width: `${passwordValidation.score}%`,
                                                backgroundColor: getPasswordStrengthColor(passwordValidation.strength)
                                            }}
                                        ></div>
                                    </div>
                                    {passwordValidation.errors.length > 0 && (
                                        <div className="password-errors">
                                            {passwordValidation.errors.map((error, index) => (
                                                <div key={index} className="password-error">
                                                    • {error}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </>
                    )}

                    <button
                        type="submit"
                        className="submit-button"
                        disabled={isLoading || (!isLogin && (passwordValidation !== null && !passwordValidation.isValid || usernameValidation !== null && !usernameValidation.isValid))}
                    >
                        {isLoading ? '处理中...' : (isLogin ? '登录' : '注册')}
                    </button>
                </form>

                <div className="form-footer">
                    <p>
                        {isLogin ? '还没有账号？' : '已有账号？'}
                        <button 
                            type="button" 
                            className="toggle-button"
                            onClick={toggleMode}
                        >
                            {isLogin ? '立即注册' : '立即登录'}
                        </button>
                    </p>
                </div>
            </div>

            <style jsx>{`
                .login-container {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px;
                }

                .login-form-container {
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
                    width: 100%;
                    max-width: 420px;
                }

                .login-header {
                    text-align: center;
                    margin-bottom: 30px;
                }

                .login-title {
                    font-size: 28px;
                    font-weight: 700;
                    color: #333;
                    margin-bottom: 8px;
                }

                .login-subtitle {
                    color: #666;
                    font-size: 16px;
                    margin: 0;
                }

                .login-form {
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }

                .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                .form-label {
                    font-weight: 600;
                    color: #333;
                    font-size: 14px;
                }

                .form-input {
                    width: 100%;
                    padding: 12px 16px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    font-size: 16px;
                    transition: border-color 0.3s, box-shadow 0.3s;
                }

                .form-input:focus {
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }

                .password-input-container {
                    position: relative;
                }

                .password-toggle {
                    position: absolute;
                    right: 12px;
                    top: 50%;
                    transform: translateY(-50%);
                    background: none;
                    border: none;
                    color: #666;
                    cursor: pointer;
                    font-size: 14px;
                }

                .password-strength-container {
                    margin-top: 8px;
                }

                .password-strength-header {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 6px;
                    font-size: 14px;
                }

                .password-strength-text {
                    font-weight: 600;
                }

                .password-strength-bar {
                    height: 6px;
                    background-color: #f0f0f0;
                    border-radius: 3px;
                    overflow: hidden;
                }

                .password-strength-fill {
                    height: 100%;
                    transition: width 0.3s, background-color 0.3s;
                }

                .password-errors {
                    margin-top: 8px;
                    color: #ff4d4f;
                    font-size: 12px;
                }

                .password-error {
                    margin-bottom: 2px;
                }

                .submit-button {
                    padding: 14px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: opacity 0.3s;
                    margin-top: 10px;
                }

                .submit-button:hover:not(:disabled) {
                    opacity: 0.9;
                }

                .submit-button:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                }

                .form-footer {
                    text-align: center;
                    margin-top: 24px;
                    color: #666;
                    font-size: 14px;
                }

                .toggle-button {
                    background: none;
                    border: none;
                    color: #667eea;
                    font-weight: 600;
                    cursor: pointer;
                    margin-left: 5px;
                    text-decoration: underline;
                }

                .toggle-button:hover {
                    color: #5a67d8;
                }

                .username-requirements {
                    margin-top: 8px;
                    padding: 10px;
                    background-color: #f8f9fa;
                    border-radius: 6px;
                    font-size: 12px;
                    color: #666;
                }

                .requirements-title {
                    font-weight: 600;
                    margin-bottom: 6px;
                    color: #333;
                }

                .requirement-item {
                    margin-bottom: 2px;
                }

                .username-errors {
                    margin-top: 8px;
                    color: #ff4d4f;
                    font-size: 12px;
                }

                .username-error {
                    margin-bottom: 2px;
                }
                
                .auto-register-notice {
                    margin-top: 16px;
                    padding: 12px;
                    background-color: #e6f7ff;
                    border: 1px solid #91d5ff;
                    border-radius: 6px;
                    font-size: 14px;
                    color: #1890ff;
                }
                
                .auto-register-notice p {
                    margin: 0;
                }
            `}</style>
        </div>
    );
}
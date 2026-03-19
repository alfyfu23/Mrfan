/**
 * 检测当前主题模式的工具函数
 */

/**
 * 检测当前是否为深色模式
 * @returns {boolean} 如果是深色模式返回true，否则返回false
 */
export const isDarkMode = (): boolean => {
    // 检查是否在浏览器环境中
    if (typeof window === 'undefined') {
        return false;
    }
    
    // 方法1：检查CSS媒体查询
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return true;
    }
    
    // 方法2：检查html元素是否有data-theme="dark"属性
    const htmlElement = document.documentElement;
    if (htmlElement.getAttribute('data-theme') === 'dark') {
        return true;
    }
    
    // 方法3：检查CSS自定义属性
    const computedStyle = window.getComputedStyle(document.documentElement);
    const backgroundColor = computedStyle.getPropertyValue('--background').trim();
    
    // 如果背景色是深色（接近黑色），则认为是深色模式
    if (backgroundColor && (
        backgroundColor.includes('0a0a0a') || 
        backgroundColor.includes('#0a0a0a') || 
        backgroundColor.includes('rgb(10, 10, 10)') ||
        backgroundColor.includes('#000') ||
        backgroundColor.includes('rgb(0, 0, 0)')
    )) {
        return true;
    }
    
    return false;
};

/**
 * 根据主题模式返回适当的颜色
 * @param {string} lightColor 浅色模式下的颜色
 * @param {string} darkColor 深色模式下的颜色
 * @returns {string} 根据当前主题返回适当的颜色
 */
export const getThemedColor = (lightColor: string, darkColor: string): string => {
    return isDarkMode() ? darkColor : lightColor;
};

/**
 * 获取当前主题下的文本颜色
 * @returns {string} 当前主题下的文本颜色
 */
export const getTextColor = (): string => {
    return getThemedColor('#333333', '#ffffff');
};

/**
 * 获取当前主题下的辅助文本颜色
 * @returns {string} 当前主题下的辅助文本颜色
 */
export const getSecondaryTextColor = (): string => {
    return getThemedColor('#666666', 'rgba(255, 255, 255, 0.7)');
};

/**
 * 获取当前主题下的背景颜色
 * @returns {string} 当前主题下的背景颜色
 */
export const getBackgroundColor = (): string => {
    return getThemedColor('#ffffff', '#0a0a0a');
};
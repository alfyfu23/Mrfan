/**
 * 密码强度验证工具
 * 根据后端要求实现密码强度检查
 */

// 密码强度类型
export type PasswordStrength = 'weak' | 'medium' | 'strong' | 'very-strong';

// 密码验证结果
export interface PasswordValidationResult {
  isValid: boolean;
  strength: PasswordStrength;
  errors: string[];
  score: number; // 0-100 分
}

// 密码强度检查函数
export function validatePasswordStrength(password: string): PasswordValidationResult {
  const errors: string[] = [];
  let score = 0;

  // 基础要求检查（与后端保持一致）
  if (password.length < 8) {
    errors.push('密码长度至少为8位');
  } else {
    score += 20;
  }

  if (password.length > 128) {
    errors.push('密码长度不能超过128位');
  }

  if (!/[A-Za-z]/.test(password)) {
    errors.push('密码必须包含至少一个字母');
  } else {
    score += 20;
  }

  if (!/\d/.test(password)) {
    errors.push('密码必须包含至少一个数字');
  } else {
    score += 20;
  }

  if (/\s/.test(password)) {
    errors.push('密码不能包含空格');
  }

  // 额外强度检查（仅用于显示，不影响isValid）
  if (/[A-Z]/.test(password)) {
    score += 10; // 包含大写字母
  }

  if (/[a-z]/.test(password)) {
    score += 10; // 包含小写字母
  }

  if (/[^A-Za-z0-9]/.test(password)) {
    score += 20; // 包含特殊字符
  }

  // 长度加分
  if (password.length >= 12) {
    score += 10;
  }

  // 确定密码强度
  let strength: PasswordStrength;
  if (score < 40) {
    strength = 'weak';
  } else if (score < 60) {
    strength = 'medium';
  } else if (score < 80) {
    strength = 'strong';
  } else {
    strength = 'very-strong';
  }

  // 确保分数在0-100范围内
  score = Math.min(100, Math.max(0, score));

  return {
    isValid: errors.length === 0,
    strength,
    errors,
    score
  };
}

// 获取密码强度描述
export function getPasswordStrengthDescription(strength: PasswordStrength): string {
  switch (strength) {
    case 'weak':
      return '弱';
    case 'medium':
      return '中等';
    case 'strong':
      return '强';
    case 'very-strong':
      return '非常强';
    default:
      return '未知';
  }
}

// 获取密码强度颜色
export function getPasswordStrengthColor(strength: PasswordStrength): string {
  switch (strength) {
    case 'weak':
      return '#ff4d4f'; // 红色
    case 'medium':
      return '#faad14'; // 橙色
    case 'strong':
      return '#52c41a'; // 绿色
    case 'very-strong':
      return '#1890ff'; // 蓝色
    default:
      return '#d9d9d9'; // 灰色
  }
}
/**
 * 用户名验证工具
 * 根据后端要求实现用户名格式检查
 */

// 用户名验证结果
export interface UsernameValidationResult {
  isValid: boolean;
  errors: string[];
}

// 用户名验证函数
export function validateUsername(username: string): UsernameValidationResult {
  const errors: string[] = [];
 
  // 检查是否为空
  if (!username || username.trim() === '') {
    errors.push('用户名不能为空');
    return {
      isValid: false,
      errors
    };
  }

  // 检查长度
  if (username.length < 1) {
    errors.push('用户名长度至少为1位');
  }

  if (username.length > 30) {
    errors.push('用户名长度不能超过30位');
  }

  // 检查是否包含空格
  if (/\s/.test(username)) {
    errors.push('用户名不能包含空格');
  }

  // 检查是否只包含字母、数字、下划线、点号和中文
  if (!/^[\w.\u4e00-\u9fa5]+$/.test(username)) {
    errors.push('用户名只能包含字母、数字、下划线、点号和中文');
  }

  // 检查是否以点号或下划线开头或结尾
  if (username.startsWith('_') || username.endsWith('_') || username.startsWith('.') || username.endsWith('.')) {
    errors.push('用户名不能以点号或下划线开头或结尾');
  }

  // 检查是否包含连续的下划线或点号
  if (/__/.test(username) || /\.\./.test(username)) {
    errors.push('用户名不能包含连续的下划线或点号');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

// 获取用户名格式要求描述
export function getUsernameRequirements(): string[] {
  return [
    '用户名长度为1-30位',
    '只能包含字母、数字、下划线、点号和中文',
    '不能包含空格',
    '不能以点号或下划线开头或结尾',
    '不能包含连续的下划线或点号'
  ];
}
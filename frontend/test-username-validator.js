// 简单的测试脚本来验证用户名验证功能
const { validateUsername, getUsernameRequirements } = require('./src/utils/usernameValidator.tsx');

console.log('=== 用户名格式要求 ===');
console.log(getUsernameRequirements());
console.log('\n=== 测试用例 ===');

const testCases = [
  { username: 'a', expected: true, description: '单个字符用户名' },
  { username: 'ab', expected: true, description: '两个字符用户名' },
  { username: 'a'.repeat(31), expected: false, description: '太长的用户名（31位）' },
  { username: 'a'.repeat(30), expected: true, description: '最大长度用户名（30位）' },
  { username: 'user name', expected: false, description: '包含空格' },
  { username: 'user@name', expected: false, description: '包含特殊字符' },
  { username: '_username', expected: false, description: '下划线开头' },
  { username: 'username_', expected: false, description: '下划线结尾' },
  { username: '.username', expected: false, description: '点号开头' },
  { username: 'username.', expected: false, description: '点号结尾' },
  { username: 'user__name', expected: false, description: '连续下划线' },
  { username: 'user..name', expected: false, description: '连续点号' },
  { username: 'user', expected: true, description: '有效的英文用户名' },
  { username: 'user123', expected: true, description: '有效的字母数字用户名' },
  { username: 'user_name', expected: true, description: '有效的带下划线用户名' },
  { username: 'user.name', expected: true, description: '有效的带点号用户名' },
  { username: 'user.name_123', expected: true, description: '有效的复合用户名' },
  { username: '用户名', expected: true, description: '有效的中文用户名' },
  { username: '用户123', expected: true, description: '有效的中文数字用户名' },
  { username: '用户.名', expected: true, description: '有效的中文带点号用户名' },
];

testCases.forEach(({ username, expected, description }) => {
  const result = validateUsername(username);
  const passed = result.isValid === expected;
  console.log(`${passed ? '✓' : '✗'} ${description}: "${username}"`);
  if (!passed) {
    console.log(`  预期: ${expected ? '有效' : '无效'}`);
    console.log(`  实际: ${result.isValid ? '有效' : '无效'}`);
    if (result.errors.length > 0) {
      console.log(`  错误: ${result.errors.join(', ')}`);
    }
  }
});
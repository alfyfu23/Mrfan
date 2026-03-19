#!/bin/bash

# 更新子模块的标准方式
echo "正在更新子模块..."

# 更新所有子模块到远程仓库的最新提交
git submodule update --remote --merge

echo "子模块更新完成！"

# 显示子模块状态
git submodule status

# 检查是否有子模块更新
if git diff --quiet -- SubRepo; then
    echo "没有检测到子模块更新。"
else
    echo "检测到子模块更新，正在提交主模块..."
    git add .
    git commit -m "Update submodules to latest commits"
    echo "提交完成！"
fi
#!/bin/bash
# describe: 简单测试脚本 - 用于测试API解析和执行
# param: name - 用户名称
# param: count=2 - 循环次数
# param: delay=1 - 延迟秒数

echo "=== 简单测试脚本开始 ==="
echo "执行时间: $(date)"
echo "用户名称: ${name}"
echo "循环次数: ${count}"
echo "延迟秒数: ${delay}"
echo ""

echo "开始循环执行..."
for i in $(seq 1 ${count}); do
    echo "第 $i 次循环: Hello ${name}!"
    if [ $i -lt ${count} ]; then
        echo "等待 ${delay} 秒..."
        sleep ${delay}
    fi
done

echo ""
echo "=== 脚本执行完成 ==="
echo "总共执行了 ${count} 次循环"
echo "完成时间: $(date)"

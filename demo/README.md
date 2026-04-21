# Reverse-Engineering Demo

这个 demo 用来模拟你内部真正想做的事情：

- 目标对象是一个不开源的 wheel / CLI 工具
- 需要多个 agent 并行探索
- 需要主控脚本持续监督，避免 agent 中途停工
- 需要把结论沉淀成 AI 友好的结构化文档

## 内容

- [demo/blackbox_whl/build_demo_blackbox.py](/home/kgx/code/kernel/model2dsl/demo/blackbox_whl/build_demo_blackbox.py)
  用来构造本地 demo wheel。
- [demo/blackbox_whl/README.md](/home/kgx/code/kernel/model2dsl/demo/blackbox_whl/README.md)
  说明这个黑盒目标怎么用。
- [scripts/orchestrate_agents.py](/home/kgx/code/kernel/model2dsl/scripts/orchestrate_agents.py)
  多 agent orchestration 骨架，已支持：
  - 多 worktree
  - 多 prompt
  - session resume
  - 停滞检测
  - 可选 judge

## 建议你内部 agent 学的点

1. 目标对象要替换成你真实的 wheel / `swft`
2. 模块切分要替换成你真实的 API 模块
3. prompt 里要强制要求：
   - 写 probe
   - 跑编译
   - 看产物
   - 覆盖对齐边界
   - 更新 summary/status
4. 监督逻辑要依赖：
   - 进程状态
   - 文件产出
   - judge 判断

## 不是重点的地方

- 这个 demo wheel 本身很简单
- 它不是为了模拟真实编译器复杂度
- 它只是让你内部 agent 学“并行逆向 + 督促推进”的模式

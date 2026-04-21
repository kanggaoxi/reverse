# Demo Black-Box Wheel

这个目录提供一个本地可构造的 demo wheel，用来模拟“弱文档、黑盒编译器、需要靠 agent 并行试验逆向”的场景。

目标不是复刻 `swft`，而是给你的内部 agent 一个可模仿的工作流：

1. 准备一个 wheel 包形式的黑盒工具。
2. 给多个 agent 划分不同模块。
3. 让它们分别写输入样例、调用 CLI、收集输出、比对生成物。
4. 让主控脚本持续监督，避免 agent 半路停工。

## 构建 wheel

```bash
python3 demo/blackbox_whl/build_demo_blackbox.py
```

输出形如：

```text
demo/blackbox_whl/dist/toycc_demo-0.1.0-py3-none-any.whl
```

## wheel 内部暴露的 CLI

构建后的 wheel 提供 `toycc` 命令。它吃一个简单 DSL：

```text
api: elementwise_add
dtype: fp16
shape: [1, 16, 18, 27]
```

然后生成：

- `kernel.cce`
- `host.cpp`
- `compile.json`

其中 `compile.json` 和 `kernel.cce` 会故意暴露一些“自动 padding / 自动 shape 变换”行为，方便 agent 去逆向：

- `fp16` 下最后一维若不满足 `32B`，会向上 pad
- 某些 `api` 下若不满足 `16x16`，会继续补齐

这正对应你关心的 `32B` / `16x16` 对齐问题。

## 推荐逆向模块划分

- `module_cli_surface`
  负责摸清 CLI 参数、输入 DSL 最小语法、输出文件结构。
- `module_shapes_alignment`
  负责各种 shape、对齐、padding、lowering 行为。
- `module_api_behavior`
  负责不同 `api:` 名称是否触发不同 lowering 路径。
- `module_codegen_patterns`
  负责比对 `.cce` / `compile.json` / `host.cpp` 的对应关系。

## 这个 demo 的意义

你的内部 agent 学的是：

- 如何把一个 black-box 包拆成多个并行逆向模块
- 如何设计 probe
- 如何监督 agent 持续推进
- 如何把结果沉淀成结构化 markdown

不是学 `toycc` 本身的语法细节。

# 角色 LoRA 顺序训练（画风暂缓）

## Goal

在 `root@i-1.gpushare.com:56541` 清理旧 LoRA，保留画风快照但暂缓画风训练，依次训练 GPT 星降、诺雅、正理、维蕾塔、时空、超神六个独立角色 LoRA。AI 只检查训练集元数据，数据仅交给专用导出和训练程序使用。

## Operator update — 2026-11-08

The operator explicitly deferred style training, then appended GPT Weileita, Shikong and Chaoshen. The exact existing display name is `gpt维蕾塔` (the request used `gpt维雷塔`). The current order is Xingjiang → Nuoya → Zhengli → Weileita → Shikong → Chaoshen. Style remains deferred and must not resume automatically. Its prepared snapshot is retained. Chaoshen generation completed after discovery with 94 successes and 44 failed groups; export only final successful, non-discarded/non-purged images. Do not regenerate failed groups.

The operator then required overlapping training with later uploads instead of waiting for the entire remote transfer. The original three character snapshots are already present remotely. Bootstrap immutable plan/queue/manifests, fully verify each ready dataset, and start Xingjiang while later datasets continue uploading. Each next character waits only for its own complete verified dataset and the previous character's successful artifacts; uploading must never modify a ready/training dataset or running controller source.

## Background

- 操作人于 2026-11-08 同意创建任务并进入规划。
- 服务器已通过本机 `~/.ssh/gpushare_ed25519` 连接；GPU 为 RTX 4090，显存 49140 MiB，当前有旧训练占用 GPU。
- 本机已有 `~/lora-kit/`，底模是 NoobAI-XL v1.1 eps；训练基线见 `train_template.sh`，无需从头搭建。
- 训练触发词使用 `aoqi` 直接拼接前缀，见 `apps/web/README.md:52`；操作人已有的 README 修改须保留。
- 生产 SQLite schema 13。下列数量通过只读状态查询、丢弃/清理标记和文件 stat 得到，未打开任何训练图片或训练文本。

| 用途 | 训练集 | 固定运行 ID | 可用图片 |
| --- | --- | --- | ---: |
| 画风 | 识破biji | 0755bcbb-0110-4d89-9c74-eb436569dae0 | 97 |
| 画风 | 识破gn | 63013341-506f-4d11-8097-d1e45632a6e6 | 95 |
| 画风 | 识破maid | a1b5ea28-d100-4584-bd0f-d94466852a1a | 87 |
| 画风 | 识破swim | 60e5db07-05b6-4061-a60b-ccc60af56ca7 | 98 |
| 画风 | 识破礼服 | b87e3356-4630-4a51-8285-acd5114d1627 | 77 |
| 画风 | 脸部 | bc7026e2-cbbe-470f-b8c7-de6eee3dc858 | 10 |
| 画风 | 无人物 | c930b1cc-92a3-4231-8904-1995784e1c65 | 15 |
| 角色 1 | gpt星降 | 9bbc6034-e756-4aa9-951e-e70a68651948 | 132 |
| 角色 2 | gpt诺雅 | bf742ebd-a6af-4fb3-8bf0-033b61162900 | 136 |
| 角色 3 | gpt正理 | ef49378c-ac5d-4f8e-a320-2a8443e49559 | 138 |
| 角色 4 | gpt维蕾塔 | b832d415-1488-4aab-879c-9f3f464bddb2 | 134 |
| 角色 5 | gpt时空 | 748af765-72f8-41ec-91cb-b6f6571dde83 | 114 |
| 角色 6 | gpt超神 | 77cf8b27-5270-407d-b08f-ea88281246ae | 94 |

画风共 479 张，三个角色共 406 张。初次检查均无未标记的缺失图片；生成失败的组不自动重跑。最终数量以导出时最新的丢弃/永久删除标记为准。

## Requirements

- R1：先检查并停止与本次目标冲突的该服务器旧训练队列，删除该服务器旧 LoRA 权重；保留 NoobAI 底模、训练环境和源训练集。清理操作只作用于经过清单核对的旧 LoRA。
- R2：只合并上表七个画风训练集，不额外加入“识破和服”、旧画风集或其他版本；同名未生成图片的空任务不加入。
- R3：画风训练每轮混洗样本，避免按服装来源顺序连续训练；图像与原标注保持配对。
- R4：画风暂缓，严格依序训练 gpt星降 → gpt诺雅 → gpt正理 → gpt维蕾塔 → gpt时空 → gpt超神；角色各自独立训练于同一底模，不把上一个角色或画风权重作为下一个训练初始权重。
- R5：训练集名称、运行 ID、状态、图片数量、文件大小、校验和等元数据可查。AI 不查看/解析图片、参考图、caption 或数据库中的训练提示词；不得回显训练内容。数据导出与加载由专用程序执行，日志/报错须防止泄露内容。
- R6：使用训练时最新筛选结果，排除丢弃和已永久删除的图片，尊重已有训练词覆盖。训练触发词统一使用 `aoqi` 前缀。
- R7：队列可脱离 SSH 持续运行，只在当前任务成功且产物校验通过后启动下一项；失败时停止并记录状态。保留分轮权重、最终权重和校验和，并有本机可查询的进度记录。
- R8：逐角色校验数据就绪状态；已完整上传的角色立即训练，同时上传尚未就绪的后续角色。就绪标记绑定固定计划和清单哈希；未完整上传或校验失败的角色不得启动，已就绪数据和运行中控制器不得被上传覆盖。

## Acceptance Criteria

- [x] A1 / R1：旧队列不再提交任务；已核对清单中的旧远端 LoRA 已删除，底模与源训练数据保留。见 `operations.md` 和 `research/cleanup-result.json`。
- [x] A2 / R2、R6：保留原十个固定运行 ID 的既有快照，追加上述三个固定角色运行 ID；六个角色相互独立，可用数量变化有元数据记录。见 `research/queue-extension-preparation-status.json`。
- [x] A3 / R3：实现并通过合成数据验证图片/标注配对及跨来源混洗；训练加载器每轮实际混洗样本，caption 混洗不作为图片混洗的替代。见 `operations.md` 和 `research/training-environment.md`。
- [ ] A4 / R4、R7：只有一个 GPU 训练进程；顺序固定，失败不误判完成，也不越过失败项启动后续角色。
- [ ] A5 / R5：操作记录和报告没有任何训练图片、caption、私有提示词或参考图内容；验证只使用合成数据和允许的元数据。
- [ ] A6 / R7：六个角色均有最终 `.safetensors`、分轮存档与 SHA-256；画风状态明确为 deferred；断开 SSH 后队列继续，进度/完成/失败状态可查询。
- [x] A7 / R8：远端星降训练与后续角色上传实际重叠；逐集就绪校验、损坏拦截和已就绪数据不可覆盖通过 41 项合成测试及允许的运行元数据确认。见 `research/incremental-overlap-timestamps.json`、`research/incremental-runtime-overlap.json`。

## Out of Scope

- 修改生成网站产品功能、重新生成训练图片、人工看图筛选或内容评价。
- 删除底模、生产源数据、本机以往已下载的 LoRA、另一台 GPU 服务器产物。
- 自动释放 GPU 实例；训练成功仅表示流程与权重产物成功，视觉效果由操作人验收。

## Planning Status

需求已收敛，设计和执行计划已准备；操作人以“开始”明确批准最终方案，进入执行。

# AGENTS.md

本文件为 AI Agent 在当前仓库中维护与扩展表情包的操作指南。

---

## 1. 项目定位与背景

- **项目用途**：本项目为 [AstrBot 表情包管理器插件](https://github.com/anka-afk/astrbot_plugin_meme_manager) 的自用表情包资源仓库。
- **协议依据**：遵循 [AstrBot 表情包协议规范 (astrbot-meme-pack-index)](https://github.com/anka-afk/astrbot-meme-pack-index)。
- **自用原则**：本仓库作为个人/团队自用表情包，**不要求**提交至社区索引广场收录，但**必须严格遵守**协议中关于目录结构、清单格式（Schema v1）以及逐图语义描述（Semantic Metadata v2.0）的规范，以便 AstrBot 能进行准确的分类选图与语义检索。

---

## 2. 环境与命令规范

- **操作系统**：Windows 环境。
- **Python 调用方式**：终端中统一使用 `py` 命令调用 Python（例如 `py scripts/manage_memes.py <cmd>`）。
- **网络代理配置**：
  - 本地代理端口为 **`10808`**。
  - 需要拉取网络资源或通过 pip 安装依赖时，使用：
    ```bash
    # curl 示例
    curl -sL --proxy http://127.0.0.1:10808 <URL>

    # pip 安装依赖示例
    py -m pip install --proxy http://127.0.0.1:10808 <package>
    ```

---

## 3. 表情包核心协议规范

### 3.1 目录组织结构

```text
astrbot-meme-pack/
├── manifest.json              # 表情包清单配置（Schema v1）
├── semantic_metadata.json     # 逐图语义元数据（Schema v2.0）
├── memes/                     # 表情包图片分类目录
│   ├── <category>/            # 分类子目录（只能有一级目录，与 manifest 中的分类一致）
│   │   └── <image_file>       # 表情图片
├── previews/                  # 封面及预览图
│   └── cover.jpg
├── schemas/                   # 本地 JSON Schema 校验定义文件
│   ├── meme-pack-manifest.schema.json
│   └── meme-pack-semantic.schema.json
└── scripts/
    └── manage_memes.py        # 表情包管理与校验脚本
```

- 图片支持格式：`.png`、`.jpg`、`.jpeg`、`.gif`、`.webp`。
- 表情路径必须且只能为：`memes/<category>/<filename>.<ext>`，禁止跨层级或逃逸包根目录。

### 3.2 清单规范 (`manifest.json`)

- `schema_version`: 整数 `1`。
- `id`: 小写字母、数字及 `._-`，如 `astrbot-meme-pack`。
- `categories`: 分类映射字典，每个分类键必须包含 `description` 说明触发场景与语气。
- `extensions.semantic`: 声明语义扩展支持：
  ```json
  "extensions": {
    "semantic": {
      "version": 1,
      "file": "semantic_metadata.json"
    }
  }
  ```
- **注意**：`manifest.json` 严格限制字段，禁止出现非 Schema 字段（如 `maintainer` 属于社区索引字段，在包清单中应使用 `author`）。

### 3.3 逐图语义元数据规范 (`semantic_metadata.json`)

- `schema_version`: 字符串 `"2.0"`。
- `pack_id`: 必须与 `manifest.json` 中的 `id` 完全一致。
- `images`: 以图片的 `entry_id` 为键的对象集合。
- **条目哈希与唯一身份（entry_id）计算算法**：
  ```text
  entry_id = SHA256(content_sha256 + "\0" + category + "\0" + relative_path)
  ```
  - `content_sha256`: 图片文件原始字节的 SHA-256 小写十六进制。
  - `category`: 分类名（如 `sigh`）。
  - `relative_path`: `memes/<category>/<filename>`。
  - `\0`: 空字符（NUL 字节 `\x00`）。
- 字段结构：
  ```json
  {
    "entry_id": "<64位SHA256>",
    "content_sha256": "<64位SHA256>",
    "relative_path": "memes/<category>/<filename>",
    "category": "<category>",
    "caption": "详细的情景与情绪描述...",
    "caption_status": "done",
    "tags": ["标签1", "标签2"],
    "visible_text": "图片内文字（若无留空）"
  }
  ```

---

## 4. 辅助脚本使用指引

项目内置纯标准库与 jsonschema 驱动的脚本 `scripts/manage_memes.py`：

```bash
# 1. 校验当前表情包完整性与 Schema 符合性
py scripts/manage_memes.py check

# 2. 计算指定图片的 content_sha256 与 entry_id
py scripts/manage_memes.py calc <图片路径> <分类名称>

# 3. 扫描 memes/ 目录，检查未被语义元数据收录的图片
py scripts/manage_memes.py sync
```

---

## 5. 新增表情包的标准 Agent 工作流

当用户或 Agent 需要向本项目添加新的表情包图片时，严格按照以下步骤操作：

1. **确定分类**：
   - 观察图片表达的情绪与语境，选择最合适的 `memes/<category>/` 目录（例如 `sigh`、`happy`、`fool` 等）。
   - 若引入全新分类，需在 `manifest.json` 的 `categories` 中补全该分类的适用场景描述。
2. **规范命名与存放**：
   - 禁止使用无意义的哈希散列文件名（如 `6a31c15d...jpeg`）。
   - 重命名为清晰明了的英文小写/拼音下划线名称（如 `messi_ignore_fan.jpeg`）。
   - 移动到对应分类目录：`memes/<category>/<new_name>.<ext>`。
3. **提取语义信息并更新元数据**：
   - 提取图片内文字填入 `visible_text`。
   - 归纳图片涉及的人物、事件、情绪关键词填入 `tags`。
   - 编写一段自然语言详细描述填入 `caption`，重点描述画面主体、动作表情、表达的情绪以及推荐使用的聊天语境。
   - 计算对应的 `content_sha256` 和 `entry_id`，写入 `semantic_metadata.json`。
4. **运行自检验证**：
   ```bash
   py scripts/manage_memes.py check
   ```
   必须确保校验返回 `[SUCCESS]`，无任何错误提示。

---
inclusion: always
---

# Python 环境与包管理规则

本项目使用 `.venv/` 虚拟环境，由 `uv` 管理。

## 规则

1. **Python 执行**：所有 python 命令一律使用 `.venv/bin/python`，不使用系统 `python3` 或其他解释器。
2. **包安装**：所有依赖安装一律使用 `uv pip install --python .venv/bin/python`，不使用 `pip3`、`pip`、`--break-system-packages` 或其他方式。
3. **代码变更后重装**：修改包源码后需要重新安装时，运行：
   ```bash
   uv pip install --python .venv/bin/python --reinstall ./roboweave_interfaces[dev] ./roboweave_control ./roboweave_safety ./roboweave_runtime ./roboweave_perception ./roboweave_planning ./roboweave_data ./roboweave_cloud_agent ./roboweave_vla
   ```
4. **测试执行**：运行 pytest 使用 `.venv/bin/python -m pytest`。
5. **禁止**：不要尝试 `python`、`python3`、系统级 pip、conda 或其他环境。不要自行探测可用的 Python 解释器。直接用 `.venv/bin/python`。

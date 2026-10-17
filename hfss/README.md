# HFSS automation

`preflight.py`只检查本机 Python、PyAEDT和 AEDT安装，不把安装存在解释为许可证或求解通过。

`build_and_solve.py`读取 `results/tables/selected_geometry.csv`，计划建立：

- 20 mm × 10 mm固定馈入口和40 mm直段；
- 四面渐变到入选开口的矩形喇叭口；
- 10模 Driven Modal波端口；
- 30 GHz自适应设置、PML和无限远场球；
- 每个端口模式的复数 `ETheta/EPhi` E/H面数据。

```powershell
D:\Miniconda3\python.exe hfss\preflight.py --project-root .
D:\Miniconda3\python.exe hfss\build_and_solve.py --project-root .
D:\Miniconda3\python.exe hfss\build_and_solve.py --project-root . --solve
```

正式状态只看 `results/hfss/hfss_status.json`。当前本机为 `BLOCKED`：AEDT 2025 R2能启动并新建项目，但 PyAEDT 0.9.6无法插入 HFSS设计；底层 `InsertDesign`探测也返回空设计列表，许可证未验证。

即使以后求解成功，端口模式最初也只标记为 `PortMode 1..10`。只有与解析 TE/TM口径模板的复数场相关系数达到0.95后，才能写入模号并合成最终多模权重；不能按端口序号猜测 TE/TM标签。

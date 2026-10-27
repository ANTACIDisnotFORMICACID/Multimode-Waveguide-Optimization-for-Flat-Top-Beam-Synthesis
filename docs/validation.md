# 数值计算与全波角谱核验

本文档说明波导模式、解析远场和 HFSS 复数远场的计算对象与数据来源。各方向图按自身峰值归一化；主区为 $\theta\leq20^\circ$，区外为 $\theta\geq40^\circ$。解析模型与全波模型各自确定模态权重，因此分别报告其指标。

## 1. 解析模型与数值实现

30 GHz、20 × 10 mm 馈入口按精确真空光速有 12 个严格传播模式。MATLAB 的 TE/TM 场计算包括截止频率、传播常数、PEC 边界和 1 W 模态功率归一化。核心测试共 13 项。直接口径积分与二维 FFT 独立计算矢量远场；在初始 10 模阶段，E/H 面归一化功率 RMSE 分别为 $2.94\times10^{-7}$ 和 $8.77\times10^{-8}$，峰值方向一致。

几何研究固定馈入口，扫描喇叭开口和长度。初始 10 模阶段在 40 × 20 × 60 mm 几何上得到五模 E/H 主切面综合：最坏主区波纹 0.858 dB、H 面半功率波束宽度 50.44°、区外最大电平 −9.542 dB。精确 12 模重算选出 60 × 20 × 60 mm 几何；进一步采用 12 条子午面进行二维角域优化，得到主区波纹 8.35 dB、区外最大电平 −13.26 dB。两组数据分别描述主切面综合与二维角域综合。

## 2. HFSS 模态与口径相位

HFSS 几何采用 20 × 10 mm 馈入口、60 × 20 mm 开口和 60 mm 渐变段，工作频率 30 GHz。端口专用求解给出 12 组传播常数，与解析模式分组的最大相对差为 1.14%。端口 1 单模与解析口径模型的 E 面方向图 RMSE 为 1.00 dB；由几何确定的二次口径相位将 H 面 RMSE 从 17.44 dB 变为 2.83 dB。这一比较显示了有限喇叭中的开口相位对方向图的作用。

## 3. 全波复数场上的模态综合

全波综合直接取原生模态激励参考下的复数 $E_\theta,E_\phi$。端口 1、5、8 的入射幅度为 0.821809、0.513387、0.247111；以端口 1 为参考，相位为 0°、15.553°、−11.010°。同一权重写入 AEDT `EditSources` 后，直接报告与离线 $\sum_j w_j\mathbf E_j$ 的复数相对误差为 $6.15\times10^{-16}$。

15 轮网格的完整二维前半空间角谱如下：

| 激励 | $\theta\leq20^\circ$ 主区波纹 | $\theta\geq40^\circ$ 区外最大电平 | 峰值极角 |
|---|---:|---:|---:|
| 端口 1 | 10.579 dB | −14.141 dB | 0° |
| 端口 1+5+8 | 5.222 dB | −10.164 dB | 11.5° |

三模合成使二维主区波纹降低 5.357 dB。主区展宽时，角谱能量向较大角度重新分配，因而区外最大电平相应变化。该指标对应全波嵌入场上的三模权重；解析六模设计采用独立的口径映射和权重。

## 4. 网格与数据一致性

固定三模权重在 12、15 轮网格上的完整二维方向图，在高于 −20 dB 的角域中归一化电平 RMSE 为 0.067 dB；端口 1 单模为 0.043 dB。两次计算的三模峰值极角均为 11.5°，主区波纹分别为 5.208/5.222 dB，区外电平为 −10.198/−10.164 dB。15 轮复数远场与独立 E/H 切面报告的逐样本相对误差约为 $1.12\times10^{-12}$。

## 5. 原始数据

- 解析模式、基线与优化数据：[`results/tables`](../results/tables/)、[`results/studies/twelve_mode_20261025`](../results/studies/twelve_mode_20261025/)、[`results/studies/full_azimuth_refinement`](../results/studies/full_azimuth_refinement/)。
- 端口模式传播常数：[`port_only_native_validation_20261026`](../results/hfss/port_only_native_validation_20261026/)。
- HFSS 三模二维综合与 AEDT 直接激励对照：[`three_mode_2d_intrinsic_20261027`](../results/hfss/twelve_mode_60x20x60_three_mode_2d_intrinsic_20261027/)、[`three_mode_intrinsic_composite_check_20261027`](../results/hfss/twelve_mode_60x20x60_three_mode_intrinsic_composite_check_20261027/)。
- 15 轮二维复数场和 12/15 轮角谱对照：[`full_azimuth_intrinsic_20261028`](../results/hfss/twelve_mode_60x20x60_iterative_15pass_full_azimuth_intrinsic_20261028/)、[`full_azimuth_comparison_20261028`](../results/hfss/twelve_mode_60x20x60_iterative_15pass_full_azimuth_comparison_20261028/)。

图件与进一步的全波分析见 [HFSS 结果说明](../hfss/README.md)。

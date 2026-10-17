# 理论模型

## 1. 坐标、截止与传播集合

馈入矩形波导沿 `+z`传播，宽边 `a=20 mm`沿 x，窄边 `b=10 mm`沿 y，工作频率 `f=30 GHz`。自由空间波数、截止波数和传播常数为

\[
k_0=\frac{2\pi f}{c_0},\qquad
k_c^2=\left(\frac{m\pi}{a}\right)^2+\left(\frac{n\pi}{b}\right)^2,
\]

\[
f_c=\frac{c_0}{2}\sqrt{\left(\frac{m}{a}\right)^2+\left(\frac{n}{b}\right)^2},\qquad
\beta=\sqrt{k_0^2-k_c^2}.
\]

只有严格满足 `fc < f`的模式进入传播集合。TE模式允许一个下标为零但禁止 TE00；TM模式要求 `m,n≥1`。TE02、TE40恰位于30 GHz截止边界，只列入目录。

## 2. TE/TM矢量场与功率归一化

代码从 TE模式的 `Hz`或 TM模式的 `Ez`出发，由 Maxwell方程分别计算 `Ex,Ey,Hx,Hy`，不再使用 `Ex+1j*Ey`代替空间矢量。模态阻抗为

\[
Z_{TE}=\frac{\omega\mu}{\beta},\qquad
Z_{TM}=\frac{\beta}{\omega\epsilon}.
\]

每个模式的正向时均功率为

\[
P=\frac12\operatorname{Re}\int_A
\left(E_xH_y^*-E_yH_x^*\right)\,dA.
\]

全部场分量按 `1/sqrt(P)`缩放到1 W。理想正交模式的权重满足

\[
\sum_q|w_q|^2=1.
\]

## 3. 固定馈入口与理想缓变喇叭口

传播模式始终由20 × 10 mm馈入口定义。快速几何模型把归一化坐标中的馈入口模态形状伸展到 `A×B`开口，场幅度乘以

\[
s_E=\frac{1}{\sqrt{(A/a)(B/b)}}
\]

以保持1 W积分功率。这是理想缓变映射的上界模型，不假定扩大后的开口可以独立激励新增传播模式。

默认 `includeAperturePhaseError=false`。因此快速模型中的 `L`只参与 H/E面半张角约束

\[
\alpha_H=\tan^{-1}\frac{A-a}{2L},\qquad
\alpha_E=\tan^{-1}\frac{B-b}{2L},
\]

不声称描述有限喇叭内的反射或相位误差。代码保留可选的一阶二次相位敏感性开关，但正式结果把有限长度传播留给 HFSS验证。

当 `A=a`且 `B=b`时，模型严格退化为直波导口径；该性质由单元测试保护。

## 4. 两套独立远场实现

直接积分对每个观察方向计算

\[
F_x(k_x,k_y)=\iint_A E_x(x,y)e^{j(k_xx+k_yy)}dA,
\]

`Fy`同理，其中

\[
k_x=k_0\sin\theta\cos\phi,\qquad
k_y=k_0\sin\theta\sin\phi.
\]

FFT实现根据真实采样间隔建立

\[
k_{x,p}=\frac{2\pi p}{N_x\Delta x},\qquad
k_{y,q}=\frac{2\pi q}{N_y\Delta y},
\]

并补偿首样点坐标相位。两种方法都使用二维梯形积分端点权重；零填充只提高谱域插值密度。

谱场转换为

\[
E_\theta=F_x\cos\phi+F_y\sin\phi,
\]

\[
E_\phi=\cos\theta(-F_x\sin\phi+F_y\cos\phi).
\]

总功率方向图为 `|Eθ|²+|Eφ|²`。TE10电场沿全局 y，Ludwig-3共/交极化为

\[
E_{co}=E_\theta\sin\phi+E_\phi\cos\phi,
\qquad
E_{cross}=E_\theta\cos\phi-E_\phi\sin\phi.
\]

## 5. 优化问题

TE10相位置零以消除全局相位等价类，其余模式使用幅度和相位变量；每次解码后重新做总功率归一化。目标函数在 E/H面同时评价：

- 主区平顶功率误差；
- 余弦过渡区误差；
- 过渡区外功率；
- 主区交叉极化。

区外项权重高于普通均方拟合，但最终是否通过只由独立指标函数判断：波纹 `≤1 dB`、区外峰值 `≤−12 dB`、交叉极化 `≤−15 dB`。

几何扫描的主目标半宽为20°，过渡宽度为5°、10°、15°、20°。几何锁定后再扫描 `5:2.5:25°`九个半宽，并在相同预算下比较 PSO、LS+`fmincon`和 PSO+`fmincon`。

连续优化后按幅度选取最多6个模式，并在缩减后的变量空间重新优化。最终20°方案保留 TE10、TE20、TE30、TE11、TM11五个模式。

## 6. 可解释范围

MATLAB结果是理想 PEC口径与缓变模态映射的数值上界。它可以验证模式公式、功率归一化、FFT采样、几何趋势和优化算法，但不自动包含真实馈电网络、喇叭内反射、壁厚、法兰、材料误差或开口边缘绕射。全波与实物结果只能作为后续独立证据，不能由解析模型替代。

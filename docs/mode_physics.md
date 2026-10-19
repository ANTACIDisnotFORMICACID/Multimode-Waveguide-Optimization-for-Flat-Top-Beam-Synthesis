# 多模矩形波导的物理分析

本文档补充说明矩形波导本征模式、口径场空间节点和远场零点之间的关系。它为主项目中的喇叭口几何扫描和多模权重优化提供物理解释，但不改变正式计算所采用的矢量前向模型。

## 1. 场方程、坐标与时间约定

设矩形波导沿 $+z$ 方向延伸，宽边 $a$ 沿 $x$，窄边 $b$ 沿 $y$。内部介质均匀、线性且无源，采用 $e^{\mathrm j\omega t}$ 时间约定。频域 Maxwell 方程为

$$
\nabla\times\mathbf E=-\mathrm j\omega\mu\mathbf H,
\qquad
\nabla\times\mathbf H=\mathrm j\omega\epsilon\mathbf E,
$$

$$
\nabla\cdot(\epsilon\mathbf E)=0,
\qquad
\nabla\cdot(\mu\mathbf H)=0.
$$

由旋度方程可得到矢量 Helmholtz 方程

$$
\nabla^2\mathbf E+k_0^2\mathbf E=0,
\qquad
\nabla^2\mathbf H+k_0^2\mathbf H=0,
\qquad
k_0=\omega\sqrt{\mu\epsilon}.
$$

令场沿传播方向含有因子 $e^{-\mathrm j\beta z}$，并把场分成横向和纵向两部分：

$$
\mathbf E=\mathbf E_t+\hat{\mathbf z}E_z,
\qquad
\mathbf H=\mathbf H_t+\hat{\mathbf z}H_z.
$$

空心单导体波导不存在非零 TEM 本征解，因此模式分为

- TE 模式：$E_z=0$，以 $H_z$ 为纵向标量势；
- TM 模式：$H_z=0$，以 $E_z$ 为纵向标量势。

## 2. PEC边界与矩形本征函数

理想导体壁面满足

$$
\hat{\mathbf n}\times\mathbf E=0,
\qquad
\hat{\mathbf n}\cdot\mathbf B=0.
$$

使用平移坐标

$$
\xi=x+\frac a2\in[0,a],
\qquad
\eta=y+\frac b2\in[0,b],
$$

纵向场满足横向 Helmholtz 本征方程

$$
\left(\nabla_t^2+k_c^2\right)\Psi(\xi,\eta)=0.
$$

TE 模式在金属壁上对应纵向磁场的法向导数为零，解为

$$
H_z=H_0
\cos\left(\frac{m\pi\xi}{a}\right)
\cos\left(\frac{n\pi\eta}{b}\right)e^{-\mathrm j\beta z}.
$$

TM 模式要求纵向电场在壁面为零，解为

$$
E_z=E_0
\sin\left(\frac{m\pi\xi}{a}\right)
\sin\left(\frac{n\pi\eta}{b}\right)e^{-\mathrm j\beta z}.
$$

两类模式具有相同形式的截止波数和色散关系：

$$
k_c^2=\left(\frac{m\pi}{a}\right)^2+
\left(\frac{n\pi}{b}\right)^2,
\qquad
\beta^2=k_0^2-k_c^2.
$$

TE 模式允许一个下标为零，但 TE00 不存在；TM 模式要求 $m,n\geq1$。只有严格满足 $k_0>k_c$ 时 $\beta$ 才为正实数，模式才能携带平均功率持续传播。$k_0=k_c$ 时群速度和纵向功率传输趋于零，因此截止边界不作为可控传播自由度。

## 3. 横向矢量场和功率基准

横向场由纵向势的横向梯度得到。对 TE 模式，电场分量具有形式

$$
E_x\propto
\frac{n\pi}{b}
\cos\left(\frac{m\pi\xi}{a}\right)
\sin\left(\frac{n\pi\eta}{b}\right),
$$

$$
E_y\propto-
\frac{m\pi}{a}
\sin\left(\frac{m\pi\xi}{a}\right)
\cos\left(\frac{n\pi\eta}{b}\right).
$$

TM 模式的两个横向电场分量分别包含余弦与正弦的乘积。因而模式下标具有直接的空间含义：增加 $m$ 会增加宽边方向的节点，增加 $n$ 会增加窄边方向的节点。TE 与 TM 模式即使具有相同的 $(m,n)$，矢量方向、阻抗以及纵向分量也不同。

第 $q$ 个模式的正向时均功率为

$$
P_q=\frac12\operatorname{Re}
\iint_A
\left(E_{x,q}H_{y,q}^{*}-E_{y,q}H_{x,q}^{*}\right)\,\mathrm dA.
$$

项目将每个模式的全部场分量同时乘以 $1/\sqrt{P_q}$，使其均对应1 W传播功率。这样，模式图谱中的形状比较与优化中的复权重具有统一功率基准，不会把临近截止模式较大的场幅误认为更多输入功率。

## 4. TE_m0模式的奇偶性和正前方零点

对 TE$_{m0}$ 模式，$E_x=0$，口径电场简化为

$$
E_y(\xi)\propto
\sin\left(\frac{m\pi\xi}{a}\right).
$$

其 H 面谱函数包含一维积分

$$
F_{y,m}(k_x)\propto
b\int_0^a
\sin\left(\frac{m\pi\xi}{a}\right)
e^{\mathrm jk_x\xi}\,\mathrm d\xi.
$$

正前方对应 $k_x=0$：

$$
F_{y,m}(0)=
\frac{ab}{m\pi}\left[1-(-1)^m\right].
$$

因此：

- 奇数 $m$ 的口径积分非零，可以在正前方形成辐射；
- 偶数 $m$ 的正、负半区面积相等，正前方复场严格相消；
- 当观察角偏离零度时，指数相位因子破坏原有相消，偶数阶模式产生一对轴外峰；
- 更高阶模式包含更多符号交替区，远场谱中也出现更多零点和瓣。

这一规律解释了为什么 TE20 适合用于削弱中心峰值并向主区两侧重新分配能量。它并不意味着所有高阶模式的峰值都随阶数单调外移；二维模式、极化投影以及有限口径共同决定实际峰值位置。

## 5. 二维模式与矢量远场

对一般 TE$_{mn}$ 或 TM$_{mn}$ 模式，口径场由 $x$、$y$ 两个方向的有限区间正弦和余弦函数相乘。其二维傅里叶谱因此具有可分结构，但两个电场分量的奇偶性和权重不同。观察方向与谱坐标之间满足

$$
k_x=k_0\sin\theta\cos\phi,
\qquad
k_y=k_0\sin\theta\sin\phi.
$$

项目分别计算

$$
F_x=\iint_A E_xe^{\mathrm j(k_xx+k_yy)}\,\mathrm dA,
\qquad
F_y=\iint_A E_ye^{\mathrm j(k_xx+k_yy)}\,\mathrm dA,
$$

再投影到球坐标分量：

$$
E_\theta=F_x\cos\phi+F_y\sin\phi,
$$

$$
E_\phi=\cos\theta(-F_x\sin\phi+F_y\cos\phi).
$$

总功率方向图为 $|E_\theta|^2+|E_\phi|^2$。这种矢量处理保留了局部极化方向，避免使用 $E_x+\mathrm jE_y$ 复标量时把空间方向与时间相位混为一谈。

README中的传播模式远场图谱只包含30 GHz下严格满足 $f_c<f$ 的模式。每格按自身峰值归一化，用于比较节点和角域对称性，不用于比较不同模式的绝对增益。

## 6. 多模干涉为何能够整形方向图

设第 $q$ 个1 W归一化模式的口径场和远场分别为 $\mathbf E_{t,q}$、$\mathbf F_q$。多模组合为

$$
\mathbf E_t=\sum_qw_q\mathbf E_{t,q},
\qquad
\mathbf F=\sum_qw_q\mathbf F_q.
$$

虽然复场对权重是线性的，辐射功率包含模式间交叉项：

$$
|\mathbf F|^2=
\sum_q|w_q|^2|\mathbf F_q|^2+
2\operatorname{Re}\sum_{p<q}
w_pw_q^*\,\mathbf F_p\cdot\mathbf F_q^*.
$$

第二项描述相干干涉。改变相对相位会改变特定角域中的相长和相消，改变幅度则调节各空间基函数的作用强度。平顶波束优化本质上是在有限传播模式张成的空间中选择复系数，使中心附近适度相消、主区边缘得到补偿，同时约束远角辐射和交叉极化。

喇叭口进一步改变基函数的有效尺度。开口增大使同一归一化场形状的傅里叶谱收窄，有利于压低远角能量，却会使宽主区边缘下降。主项目将几何扫描与模态权重优化分开，正是为了分别处理“谱尺度”和“模式干涉”这两个物理机制。

## 7. 适用范围

上述分析描述理想PEC波导口径及缓变映射模型。它没有包含有限长度反射、喇叭壁电流、开口边缘绕射、模式转换或实际馈电网络。二维模式图谱能够解释优化自由度，但不能替代全波仿真或实物方向图测量。

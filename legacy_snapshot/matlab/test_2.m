clear; clc; close all

%% 基本参数
a = 20e-3; b = 10e-3;     % 波导尺寸
f = 30e9;                 % 频率
c = 3e8;
lambda = c / f;
k0 = 2*pi/lambda;

% 网格
Nx = 128; Ny = 256; zp = 8;
x = linspace(0, a, Nx);
y = linspace(0, b, Ny);
[X, Y] = meshgrid(x, y);

% 模式 TE10
m = 1; n = 0;

% 近场电场（归一化）
[Ex, Ey, ~] = TE_field(m, n, X, Y, a, b);
E_near = Ex + 1j*Ey;

% FFT 计算
E_pad = padarray(E_near, [(zp-1)*Ny, (zp-1)*Nx], 0, 'post');
F = fftshift(fft2(E_pad));

% K空间
kx = linspace(-k0, k0, zp*Nx);
ky = linspace(-k0, k0, zp*Ny);
[KX, KY] = meshgrid(kx, ky);

% 掩码，仅显示传播波部分
mask = (KX.^2 + KY.^2) <= k0^2;
F(~mask) = 0;

%% 极坐标转换 + 映射到球面方向图
R = abs(F);
R = R / max(R(:));  % 归一化
R = R.^0.3;          % 增强可视效果

% 极角映射
[phi_k, ~] = cart2pol(KX, KY);  % φ 方位角
theta_k = asin(sqrt(KX.^2 + KY.^2) / k0);  % θ 极角

% 转为三维坐标
[Xs, Ys, Zs] = sph2cart(phi_k, theta_k, R);

%% 绘图
figure('Name','TE10 模的三维方向图','NumberTitle','off','Position',[100 100 800 700])
surf(Xs, Ys, Zs, R, 'EdgeColor', 'none')
title('TE_{10} 模远场三维方向图')
xlabel('k_x'); ylabel('k_y'); zlabel('归一化幅度')
colormap turbo
colorbar
axis equal
view(45, 30)
daspect([1 1 0.4])     % 控制立体感
lighting gouraud
camlight headlight

function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
    Ex = -1j * (n*pi/b) * cos(m*pi*X/a) .* sin(n*pi*Y/b);
    Ey =  1j * (m*pi/a) * sin(m*pi*X/a) .* cos(n*pi*Y/b);
    norm_factor = max(max(sqrt(abs(Ex).^2 + abs(Ey).^2)));
    Ex = Ex / norm_factor;
    Ey = Ey / norm_factor;
end

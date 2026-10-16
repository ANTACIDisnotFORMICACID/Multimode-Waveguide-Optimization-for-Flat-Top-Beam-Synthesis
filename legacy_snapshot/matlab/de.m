%% 优化模块：从目标远场分布反推近场模态组合（平顶方向图）
clear; clc; close all;

% ---- 参数设置 ----
a0 = 20e-3;       % 初始口径a (m)
b0 = 10e-3;       % 初始口径b (m)
f = 30e9;         % 频率30 GHz
c = 3e8;
lambda = c / f;
k0 = 2 * pi / lambda;
zp = 8;           % FFT零填充因子

% 可调导模列表
modes = {'TE10','TE01','TE11','TE20','TE02','TE21','TE12'};
Nm = numel(modes);

% 空间网格
Nx = 128; Ny = 128;
x = linspace(0, a0, Nx);
y = linspace(0, b0, Ny);
[X, Y] = meshgrid(x, y);

% k空间网格
kx = linspace(-k0, k0, zp*Nx);
ky = linspace(-k0, k0, zp*Ny);
[KX, KY] = meshgrid(kx, ky);
mask_propagate = (KX.^2 + KY.^2) <= k0^2;

% 远场角度切片
theta = linspace(-30, 30, 61);  % 缩小角度范围，单位度
phi = 0;
kx_grid = k0 * sind(theta) * cosd(phi);
ky_grid = k0 * sind(theta) * sind(phi);

% ---- 目标远场分布（平顶方向图） ----
theta_c = 1;   % 平顶半宽度 (度)
sigma = 2;     % 边缘平滑过渡宽度 (度)

target_far = zeros(size(theta));
for i = 1:length(theta)
    th = theta(i);
    if abs(th) <= theta_c
        target_far(i) = 1;
    elseif th > theta_c
        target_far(i) = exp(-((th - theta_c)^2)/(2*sigma^2));
    else
        target_far(i) = exp(-((th + theta_c)^2)/(2*sigma^2));
    end
end
target_far = target_far / max(target_far);

% ---- 优化变量 ----
% x = [A1,...An, P1,...Pn, a, b] 共2N+2个变量

% 优化变量范围放宽
lb = [zeros(1,Nm), -pi*ones(1,Nm), 5e-3, 5e-3];
ub = [ones(1,Nm), pi*ones(1,Nm), 40e-3, 30e-3]; % 最大口径放大

% 优化初始值带随机扰动，避免局部极小
rng(0);  % 固定随机种子方便复现
x0 = [0.3 + 0.4*rand(1,Nm), pi*rand(1,Nm)-pi/2, a0, b0];

% ---- 优化目标函数 ----
costfun = @(x) compute_cost(x, modes, X, Y, KX, KY, mask_propagate, kx_grid, ky_grid, target_far, zp, k0);

% ---- 调用优化器 ----
opts = optimoptions('fmincon', 'Display','iter', 'MaxIterations', 100, 'TolFun',1e-4);
[x_opt, fval] = fmincon(costfun, x0, [], [], [], [], lb, ub, [], opts);

% ---- 输出最优结果 ----
A_opt = x_opt(1:Nm);
P_opt = x_opt(Nm+1:2*Nm);
a_opt = x_opt(end-1);
b_opt = x_opt(end);

fprintf('最优口径：a = %.2f mm, b = %.2f mm\n', a_opt*1e3, b_opt*1e3);
for i = 1:Nm
    fprintf('%s: 幅度 = %.3f, 相位 = %.3f rad\n', modes{i}, A_opt(i), P_opt(i));
end

% ---- 利用最优结果重新计算远场切片 ----
[Nx, Ny] = size(X);
x2 = linspace(0, a_opt, Nx);
y2 = linspace(0, b_opt, Ny);
[X2, Y2] = meshgrid(x2, y2);

E_sum = zeros(size(X2));
for idx = 1:Nm
    [m, n] = parse_mode(modes{idx});
    kc2 = (m*pi/a_opt)^2 + (n*pi/b_opt)^2;
    if k0^2 < kc2
        continue;
    end
    [Ex, Ey, ~] = TE_field(m, n, X2, Y2, a_opt, b_opt);
    E_mode = (Ex + 1j*Ey) * A_opt(idx) * exp(1j*P_opt(idx));
    E_sum = E_sum + E_mode;
end

pad_x = Nx*(zp-1);
pad_y = Ny*(zp-1);
E_pad = padarray(E_sum, [pad_y, pad_x], 0, 'post');
F = fftshift(fft2(E_pad));
F(~mask_propagate) = 0;

E_far_slice = interp2(KX, KY, F, kx_grid, ky_grid, 'spline', 0);
E_far_slice = abs(E_far_slice);
E_far_slice = E_far_slice / max(E_far_slice + eps);

% ---- 绘制目标远场与优化远场对比 ----
figure;
plot(theta, target_far, 'k--', 'LineWidth', 1.5); hold on;
plot(theta, E_far_slice, 'r-', 'LineWidth', 2);
legend('目标远场', '优化结果');
xlabel('\theta (度)');
ylabel('归一化强度');
title('远场方向图比较');
grid on;

% ---- 子函数定义 ----

function err = compute_cost(x, modes, X, Y, KX, KY, mask_propagate, kxg, kyg, target_far, zp, k0)
    Nm = numel(modes);
    amp = x(1:Nm);
    phase = x(Nm+1:2*Nm);
    a = x(end-1);
    b = x(end);

    [Nx, Ny] = size(X);
    x2 = linspace(0, a, Nx);
    y2 = linspace(0, b, Ny);
    [X2, Y2] = meshgrid(x2, y2);

    E_sum = zeros(size(X2));
    for idx = 1:Nm
        [m, n] = parse_mode(modes{idx});
        kc2 = (m*pi/a)^2 + (n*pi/b)^2;
        if k0^2 < kc2
            continue;
        end
        [Ex, Ey, ~] = TE_field(m, n, X2, Y2, a, b);
        E_mode = (Ex + 1j*Ey) * amp(idx) * exp(1j*phase(idx));
        E_sum = E_sum + E_mode;
    end

    pad_x = Nx*(zp-1);
    pad_y = Ny*(zp-1);
    E_pad = padarray(E_sum, [pad_y, pad_x], 0, 'post');
    F = fftshift(fft2(E_pad));
    F(~mask_propagate) = 0;

    E_far_slice = interp2(KX, KY, F, kxg, kyg, 'spline', 0);
    E_far_slice = abs(E_far_slice);
    E_far_slice = E_far_slice / max(E_far_slice + eps);

    err = mean((E_far_slice - target_far).^2);
end

function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
    Ex = -1j * (n*pi/b) * cos(m*pi*X/a) .* sin(n*pi*Y/b);
    Ey =  1j * (m*pi/a) * sin(m*pi*X/a) .* cos(n*pi*Y/b);
    norm_factor = max(max(sqrt(abs(Ex).^2 + abs(Ey).^2)));
    Ex = Ex / norm_factor;
    Ey = Ey / norm_factor;
end

function [m, n] = parse_mode(mode_str)
    tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
    m = str2double(tokens{1}{1});
    n = str2double(tokens{1}{2});
end

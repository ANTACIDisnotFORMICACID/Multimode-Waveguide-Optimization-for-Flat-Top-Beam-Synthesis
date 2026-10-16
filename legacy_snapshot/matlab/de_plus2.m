%% 粒子群优化版本：基于反向傅里叶变换的近场优化（与de_2变量一致）
clear; clc; close all;

% ---------- 参数设置 ---------- 
a0 = 20e-3; b0 = 10e-3; % 初始口径尺寸
f = 30e9;                % 频率与de_2一致
c = 3e8; lambda = c/f; k0 = 2*pi/lambda;
zp = 4;                  % 零填充因子

% 模式列表（与de_2一致）
modes = {'TE10','TE01','TE11','TE20','TE02','TE21','TE12'};
Nm = numel(modes);

% 空间网格
Nx = 128; Ny = 128;
x = linspace(0, a0, Nx); y = linspace(0, b0, Ny);
[X, Y] = meshgrid(x, y);

% ---- 预计算固定参数 ----
% k空间网格与掩码（与尺寸无关）
kx = linspace(-k0, k0, zp*Nx);
ky = linspace(-k0, k0, zp*Ny);
[KX, KY] = meshgrid(kx, ky);
mask_propagate = (KX.^2 + KY.^2) <= k0^2;

% 远场角度切片参数
theta = linspace(-30, 30, 61); phi = 0;
kx_grid = k0 * sind(theta) * cosd(phi);
ky_grid = k0 * sind(theta) * sind(phi);

% 目标远场分布（固定）
theta_c = 1; sigma = 2;
target_far = double(abs(theta) <= theta_c) + ...
    exp(-((abs(theta)-theta_c).^2)/(2*sigma^2)).*(abs(theta) > theta_c);
target_far = target_far / max(target_far);

% ---- 关键修改：反向傅里叶生成目标近场 ----
F_target = zeros(zp*Ny, zp*Nx);
idx_x = zeros(1, length(kx_grid));
idx_y = zeros(1, length(ky_grid));
for i = 1:length(theta)
    [~, idx_x(i)] = min(abs(kx - kx_grid(i)));
    [~, idx_y(i)] = min(abs(ky - ky_grid(i)));
    F_target(idx_y(i), idx_x(i)) = target_far(i);
end

% 反向FFT得到目标近场
E_target_pad = ifft2(ifftshift(F_target));
E_target = E_target_pad(1:Ny, 1:Nx);
E_target = E_target / max(abs(E_target(:)) + eps);

% ---- 优化变量设置----
lb = [zeros(1,Nm), -pi*ones(1,Nm), 5e-3, 5e-3];
ub = [ones(1,Nm), pi*ones(1,Nm), 40e-3, 30e-3];
nvars = 2*Nm + 2;

% ---- 粒子群优化配置----
opts = optimoptions('particleswarm', ...
    'Display','iter','MaxIterations',100, ...
    'SwarmSize',60, 'UseParallel',false);

% ---- 优化目标函数：近场匹配 ----
costfun = @(x) compute_cost_plus(x, modes, target_far, k0, zp, Nx, Ny, KX, KY, theta, phi);
[x_opt, fval] = particleswarm(costfun, nvars, lb, ub, opts);

% ---- 解析结果 ----
A_opt = x_opt(1:Nm); P_opt = x_opt(Nm+1:2*Nm);
a_opt = x_opt(end-1); b_opt = x_opt(end);

fprintf('最优口径：a = %.2f mm, b = %.2f mm\n', a_opt*1e3, b_opt*1e3);
fprintf('工作频率：%.1f GHz\n', f/1e9);
for i = 1:Nm
    [m, n] = parse_mode(modes{i});
    kc2 = (m*pi/a_opt)^2 + (n*pi/b_opt)^2;
    if k0^2 >= kc2
        fprintf('%s: 幅度 = %.3f, 相位 = %.3f rad\n', modes{i}, A_opt(i), P_opt(i));
    else
        fprintf('%s: 无效模式（截止）\n', modes{i});
    end
end

% ---- 生成优化后的近场并验证远场 ----
x_new = linspace(0, a_opt, Nx); y_new = linspace(0, b_opt, Ny);
[X_new, Y_new] = meshgrid(x_new, y_new);
E_sum = zeros(size(X_new));
for idx = 1:Nm
    [m, n] = parse_mode(modes{idx});
    kc2 = (m*pi/a_opt)^2 + (n*pi/b_opt)^2;
    if k0^2 < kc2, continue; end
    [Ex, Ey, ~] = TE_field(m, n, X_new, Y_new, a_opt, b_opt);
    E_sum = E_sum + (Ex + 1j*Ey) * A_opt(idx) * exp(1j*P_opt(idx));
end

% 计算优化后的远场
E_pad = padarray(E_sum, [Ny*(zp-1), Nx*(zp-1)], 0, 'post');
F_opt = fftshift(fft2(E_pad));
F_opt(~mask_propagate) = 0;
E_far_slice = interp2(KX, KY, F_opt, kx_grid, ky_grid, 'spline', 0);
E_far_slice = abs(E_far_slice); E_far_slice = E_far_slice / max(E_far_slice + eps);

% ---- 绘图 ----
figure;
plot(theta, target_far, 'k--', 'LineWidth', 1.5); hold on;
plot(theta, E_far_slice, 'r-', 'LineWidth', 2);
legend('目标远场', '优化结果');
xlabel('\theta (度)'); ylabel('归一化强度'); grid on;
title('远场方向图比较');

% ---- 成本函数 ----
function err = compute_cost_plus(x, modes, target_far, k0, zp, Nx, Ny, KX, KY, theta, phi)
    Nm = numel(modes);
    amp = x(1:Nm); phase = x(Nm+1:2*Nm);
    a = x(end-1); b = x(end);

    % 重建目标近场
    kx_grid = k0 * sind(theta) * cosd(phi);
    ky_grid = k0 * sind(theta) * sind(phi);
    F_target = zeros(zp*Ny, zp*Nx);
    for i = 1:length(kx_grid)
        [~, idx_x] = min(abs(KX(1,:) - kx_grid(i)));
        [~, idx_y] = min(abs(KY(:,1) - ky_grid(i)));
        F_target(idx_y, idx_x) = target_far(i);
    end
    E_target_pad = ifft2(ifftshift(F_target));
    E_target = E_target_pad(1:Ny, 1:Nx);
    E_target = E_target / (max(abs(E_target(:))) + eps);

    % 当前网格生成
    x_new = linspace(0, a, Nx);
    y_new = linspace(0, b, Ny);
    [X_new, Y_new] = meshgrid(x_new, y_new);

    E_sum = zeros(size(X_new));
    for idx = 1:Nm
        [m, n] = parse_mode(modes{idx});
        kc2 = (m*pi/a)^2 + (n*pi/b)^2;
        if k0^2 < kc2, continue; end
        [Ex, Ey, ~] = TE_field(m, n, X_new, Y_new, a, b);
        E_sum = E_sum + (Ex + 1j*Ey) * amp(idx) * exp(1j*phase(idx));
    end

    % 归一化误差
    E_sum_norm = E_sum / (max(abs(E_sum(:))) + eps);
    E_target_norm = E_target / (max(abs(E_target(:))) + eps);
    err = mean(abs(E_sum_norm(:) - E_target_norm(:)).^2);
end

% ---- TE 模式场函数 ----
function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
    Ex = -1j * (n*pi/b) * cos(m*pi*X/a) .* sin(n*pi*Y/b);
    Ey =  1j * (m*pi/a) * sin(m*pi*X/a) .* cos(n*pi*Y/b);
    norm_factor = max(max(sqrt(abs(Ex).^2 + abs(Ey).^2)));
    Ex = Ex / norm_factor; Ey = Ey / norm_factor;
end

% ---- 模式名解析函数 ----
function [m, n] = parse_mode(mode_str)
    tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
    m = str2double(tokens{1}{1});
    n = str2double(tokens{1}{2});
end

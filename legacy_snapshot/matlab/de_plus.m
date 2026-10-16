%% 粒子群优化版本：基于反向傅里叶变换的近场优化（固定波导尺寸）
clear; clc; close all;

% ---------- 参数设置 ---------- 
a0 = 20e-3; b0 = 10e-3; % 固定波导尺寸
f = 30e9; c = 3e8; lambda = c/f; k0 = 2*pi/lambda;
zp = 4;

% 模式列表
modes = {'TE10','TE01','TE11','TE20','TE02','TE21','TE12'};
Nm = numel(modes);

% ====== 导模截止验证：筛选有效模式 ======
valid_modes = false(1, Nm);
for idx = 1:Nm
    [m, n] = parse_mode(modes{idx});
    kc2 = (m*pi/a0)^2 + (n*pi/b0)^2;
    valid_modes(idx) = (k0^2 >= kc2);
end
active_modes = modes(valid_modes);
active_Nm = numel(active_modes);
fprintf('有效模式数量：%d/%d\n', active_Nm, Nm);

% 空间网格（基于固定a0和b0）
Nx = 128; Ny = 128;
x = linspace(0, a0, Nx); y = linspace(0, b0, Ny);
[X, Y] = meshgrid(x, y);

% k空间网格与掩码
kx = linspace(-k0, k0, zp*Nx);
ky = linspace(-k0, k0, zp*Ny);
[KX, KY] = meshgrid(kx, ky);
mask_propagate = (KX.^2 + KY.^2) <= k0^2;

% 远场角度切片
theta = linspace(-30, 30, 61); phi = 0;
kx_grid = k0 * sind(theta) * cosd(phi);
ky_grid = k0 * sind(theta) * sind(phi);

% ---- 目标远场分布：平顶方向图 ----
theta_c = 1; sigma = 2;
target_far = double(abs(theta) <= theta_c) + ...
    exp(-((abs(theta)-theta_c).^2)/(2*sigma^2)).*(abs(theta) > theta_c);
target_far = target_far / max(target_far);

% ---- 反向傅里叶生成目标近场（基于固定a0和b0）----
F_target = zeros(zp*Ny, zp*Nx);
idx_x = zeros(1,length(theta));
idx_y = zeros(1,length(theta));
for i = 1:length(theta)
    [~, idx_x(i)] = min(abs(kx - kx_grid(i)));
    [~, idx_y(i)] = min(abs(ky - ky_grid(i)));
    F_target(idx_y(i), idx_x(i)) = target_far(i);
end
E_target_pad = ifft2(ifftshift(F_target));
E_target = E_target_pad(1:Ny, 1:Nx);
E_target = E_target / max(abs(E_target(:)) + eps);

% ---- 优化变量（仅有效模式）----
lb = [zeros(1,active_Nm), -pi*ones(1,active_Nm)];
ub = [ones(1,active_Nm), pi*ones(1,active_Nm)];
nvars = 2*active_Nm;

% 启动并行池
if isempty(gcp('nocreate'))
    parpool;
end

% ---- 粒子群优化配置 ----
opts = optimoptions('particleswarm', ...
    'Display','iter','MaxIterations',300, ...
    'SwarmSize',60, 'UseParallel', true);

% ====== 优化开始 ======
fprintf('优化开始...\n');
tic;

% 修改后的成本函数
costfun = @(x) compute_cost_plus(x, active_modes, X, Y, E_target, a0, b0, k0);
[x_opt, fval] = particleswarm(costfun, nvars, lb, ub, opts);

% ====== 优化结束与输出 ======
total_time = toc;
fprintf('优化总耗时：%.2f 秒\n', total_time);

A_opt_all = zeros(1, Nm);
P_opt_all = zeros(1, Nm);
A_opt = x_opt(1:active_Nm);
P_opt = x_opt(active_Nm+1:end);
active_idx = find(valid_modes);
for i = 1:active_Nm
    A_opt_all(active_idx(i)) = A_opt(i);
    P_opt_all(active_idx(i)) = P_opt(i);
end

fprintf('固定波导尺寸：a = %.2f mm, b = %.2f mm\n', a0*1e3, b0*1e3);
fprintf('工作频率：%.1f GHz\n', f/1e9);
for i = 1:Nm
    if valid_modes(i)
        fprintf('%s: 幅度 = %.3f, 相位 = %.3f rad\n', modes{i}, A_opt_all(i), P_opt_all(i));
    else
        fprintf('%s: 无效模式（已过滤）\n', modes{i});
    end
end

% ---- 生成优化后的近场并验证远场 ----
[X_new, Y_new] = meshgrid(linspace(0, a0, Nx), linspace(0, b0, Ny));
E_sum = zeros(size(X_new));
for idx = 1:active_Nm
    [m, n] = parse_mode(active_modes{idx});
    [Ex, Ey, ~] = TE_field(m, n, X_new, Y_new, a0, b0);
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

% ---- 成本函数（仅用于有效模式）----
function err = compute_cost_plus(x, modes, X, Y, E_target, a, b, k0)
    Nm = numel(modes);
    amp = x(1:Nm); phase = x(Nm+1:2*Nm);

    [X_new, Y_new] = meshgrid(linspace(0, a, size(X,2)), linspace(0, b, size(Y,1)));
    E_sum = zeros(size(X_new));
    for idx = 1:Nm
        [m, n] = parse_mode(modes{idx});
        [Ex, Ey, ~] = TE_field(m, n, X_new, Y_new, a, b);
        E_sum = E_sum + (Ex + 1j*Ey) * amp(idx) * exp(1j*phase(idx));
    end

    err = mean(abs(E_sum(:) - E_target(:)).^2);
end

% ---- TE 模式场函数 ----
function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
    Ex = -1j * (n*pi/b) * cos(m*pi*X/a) .* sin(n*pi*Y/b);
    Ey =  1j * (m*pi/a) * sin(m*pi*X/a) .* cos(n*pi*Y/b);
    norm_factor = max(max(sqrt(abs(Ex).^2 + abs(Ey).^2)));
    Ex = Ex / norm_factor; Ey = Ey / norm_factor;
end

% ---- 模式解析函数 ----
function [m, n] = parse_mode(mode_str)
    tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
    m = str2double(tokens{1}{1});
    n = str2double(tokens{1}{2});
end


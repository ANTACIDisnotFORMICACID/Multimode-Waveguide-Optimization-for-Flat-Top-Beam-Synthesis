% %% 优化模块：使用粒子群优化加速反推近场模态组合（平顶方向图）
% clear; clc; close all;
% 
% % ---- 参数设置 ----
% a0 = 20e-3; b0 = 10e-3; f = 30e9;  % 固定波导尺寸
% c = 3e8; lambda = c / f; k0 = 2*pi/lambda; zp = 4;
% 
% % 模式列表
% modes = {'TE10','TE01','TE11','TE20','TE02','TE21','TE12'};
% Nm = numel(modes);
% 
% % 空间网格（基于固定a0和b0）
% Nx = 128; Ny = 128;
% x = linspace(0, a0, Nx);
% y = linspace(0, b0, Ny);
% [X, Y] = meshgrid(x, y);
% 
% % k空间网格与掩码
% kx = linspace(-k0, k0, zp*Nx);
% ky = linspace(-k0, k0, zp*Ny);
% [KX, KY] = meshgrid(kx, ky);
% mask_propagate = (KX.^2 + KY.^2) <= k0^2;
% 
% % 远场角度切片
% theta = linspace(-30, 30, 61); phi = 0;
% kx_grid = k0 * sind(theta) * cosd(phi);
% ky_grid = k0 * sind(theta) * sind(phi);
% 
% % ---- 目标远场分布：平顶方向图 ----
% theta_c = 1; sigma = 2;
% target_far = double(abs(theta) <= theta_c) + exp(-((abs(theta) - theta_c).^2) / (2*sigma^2)) .* (abs(theta) > theta_c);
% target_far = target_far / max(target_far);
% 
% % ---- 优化变量（仅幅度和相位）----
% lb = [zeros(1,Nm), -pi*ones(1,Nm)];  % 移除a,b的约束
% ub = [ones(1,Nm), pi*ones(1,Nm)];
% nvars = 2*Nm;  % 变量数量减少为2*Nm
% 
% % 启动并行池（若未启动）
% if isempty(gcp('nocreate'))
%     parpool;  % 默认使用所有可用核心
% end
% 
% % 配置 PSO 选项
% opts = optimoptions('particleswarm', ...
%     'UseParallel', true, ...       % 启用并行计算
%     'Display', 'iter', ...
%     'MaxIterations', 300, ...
%     'SwarmSize', 60);
% 
% % 修改成本函数：传入固定a0和b0
% costfun = @(x) compute_cost(x, modes, X, Y, KX, KY, mask_propagate, kx_grid, ky_grid, target_far, zp, k0, a0, b0);
% [x_opt, fval] = particleswarm(costfun, nvars, lb, ub, opts);
% 
% % ---- 解析结果 ----
% A_opt = x_opt(1:Nm); P_opt = x_opt(Nm+1:2*Nm);
% fprintf('固定波导尺寸：a = %.2f mm, b = %.2f mm\n', a0*1e3, b0*1e3);
% for i = 1:Nm
%     fprintf('%s: 幅度 = %.3f, 相位 = %.3f rad\n', modes{i}, A_opt(i), P_opt(i));
% end
% 
% % ---- 生成最优远场（使用固定a0和b0）----
% [X2, Y2] = meshgrid(linspace(0, a0, Nx), linspace(0, b0, Ny));
% E_sum = zeros(size(X2));
% for idx = 1:Nm
%     [m, n] = parse_mode(modes{idx});
%     kc2 = (m*pi/a0)^2 + (n*pi/b0)^2;
%     if k0^2 < kc2, continue; end
%     [Ex, Ey, ~] = TE_field(m, n, X2, Y2, a0, b0);
%     E_mode = (Ex + 1j*Ey) * A_opt(idx) * exp(1j*P_opt(idx));
%     E_sum = E_sum + E_mode;
% end
% E_pad = padarray(E_sum, [Ny*(zp-1), Nx*(zp-1)], 0, 'post');
% F = fftshift(fft2(E_pad));
% F(~mask_propagate) = 0;
% E_far_slice = interp2(KX, KY, F, kx_grid, ky_grid, 'spline', 0);
% E_far_slice = abs(E_far_slice); E_far_slice = E_far_slice / max(E_far_slice + eps);
% 
% % ---- 绘图 ----
% figure;
% plot(theta, target_far, 'k--', 'LineWidth', 1.5); hold on;
% plot(theta, E_far_slice, 'r-', 'LineWidth', 2);
% legend('目标远场', '优化结果');
% xlabel('\theta (度)'); ylabel('归一化强度'); grid on;
% title('远场方向图比较');
% 
% % ---- 修改后的子函数 ----
% function err = compute_cost(x, modes, X, Y, KX, KY, mask_propagate, kxg, kyg, target_far, zp, k0, a, b)
%     Nm = numel(modes); amp = x(1:Nm); phase = x(Nm+1:2*Nm);
%     [Nx, Ny] = size(X);
%     [X2, Y2] = meshgrid(linspace(0, a, Nx), linspace(0, b, Ny));
%     E_sum = zeros(size(X2));
%     for idx = 1:Nm
%         [m, n] = parse_mode(modes{idx});
%         kc2 = (m*pi/a)^2 + (n*pi/b)^2;
%         if k0^2 < kc2, continue; end
%         [Ex, Ey, ~] = TE_field(m, n, X2, Y2, a, b);
%         E_sum = E_sum + (Ex + 1j*Ey) * amp(idx) * exp(1j*phase(idx));
%     end
%     E_pad = padarray(E_sum, [Ny*(zp-1), Nx*(zp-1)], 0, 'post');
%     F = fftshift(fft2(E_pad));
%     F(~mask_propagate) = 0;
%     E_far = interp2(KX, KY, F, kxg, kyg, 'spline', 0);
%     E_far = abs(E_far); E_far = E_far / max(E_far + eps);
%     err = mean((E_far - target_far).^2);
% end
% 
% % TE_field 和 parse_mode 函数保持不变
% 
% function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
%     Ex = -1j * (n*pi/b) * cos(m*pi*X/a) .* sin(n*pi*Y/b);
%     Ey =  1j * (m*pi/a) * sin(m*pi*X/a) .* cos(n*pi*Y/b);
%     norm_factor = max(max(sqrt(abs(Ex).^2 + abs(Ey).^2)));
%     Ex = Ex / norm_factor; Ey = Ey / norm_factor;
% end
% 
% function [m, n] = parse_mode(mode_str)
%     tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
%     m = str2double(tokens{1}{1});
%     n = str2double(tokens{1}{2});
% end

%% 优化模块：使用粒子群优化加速反推近场模态组合（平顶方向图）——固定波导尺寸
clear; clc; close all;

% ---- 参数设置 ----
a0 = 20e-3; b0 = 10e-3; f = 30e9;  % 固定波导尺寸
c = 3e8; lambda = c / f; k0 = 2*pi/lambda; zp = 4;

% 模式列表
modes = {'TE10','TE01','TE11','TE20','TE02','TE21','TE12'};
Nm = numel(modes);

% ====== 新增：预先过滤有效模式 ======
valid_modes = false(1, Nm);
for idx = 1:Nm
    [m, n] = parse_mode(modes{idx});
    kc2 = (m*pi/a0)^2 + (n*pi/b0)^2;
    valid_modes(idx) = (k0^2 >= kc2);  % 标记有效模式
end
active_modes = modes(valid_modes);     % 有效模式列表
active_Nm = numel(active_modes);       % 有效模式数量
fprintf('有效模式数量：%d/%d\n', active_Nm, Nm);
% ====== 修改结束 ======

% 空间网格（基于固定a0和b0）
Nx = 128; Ny = 128;
x = linspace(0, a0, Nx);
y = linspace(0, b0, Ny);
[X, Y] = meshgrid(x, y);

% k空间网格与掩码
kx = linspace(-k0, k0, zp*Nx);
ky = linspace(-k0, k0, zp*Ny);
[KX, KY] = meshgrid(kx, ky);
mask_propagate = (KX.^2 + KY.^2) <= k0^2;

% 远场角度切片
theta = linspace(-30, 30,61); phi = 0;
kx_grid = k0 * sind(theta) * cosd(phi);
ky_grid = k0 * sind(theta) * sind(phi);

% ---- 目标远场分布：平顶方向图 ----
theta_c = 1; sigma = 2;
target_far = double(abs(theta) <= theta_c) + ...
    exp(-((abs(theta)-theta_c).^2)/(2*sigma^2)).*(abs(theta) > theta_c);
target_far = target_far / max(target_far);

% ---- 优化变量（仅有效模式的幅度和相位）----
lb = [zeros(1,active_Nm), -pi*ones(1,active_Nm)];  % 仅对有效模式设置约束
ub = [ones(1,active_Nm), pi*ones(1,active_Nm)];
nvars = 2*active_Nm;  % 变量数量减少

% 启动并行池（若未启动）
if isempty(gcp('nocreate'))
    parpool;  % 默认使用所有可用核心
end

% 配置 PSO 选项
opts = optimoptions('particleswarm', ...
    'UseParallel', true, ...       % 启用并行计算
    'Display', 'iter', ...
    'MaxIterations', 300, ...
    'SwarmSize', 60);

% ====== 新增：计时开始 ======
fprintf('优化开始...\n');
tic;  % 开始计时

% 修改成本函数：仅处理有效模式
costfun = @(x) compute_cost_fixed(x, active_modes, X, Y, KX, KY, mask_propagate, kx_grid, ky_grid, target_far, zp, k0, a0, b0);
[x_opt, fval] = particleswarm(costfun, nvars, lb, ub, opts);

% ====== 新增：计时结束 ======
total_time = toc;
fprintf('优化总耗时：%.2f 秒\n', total_time);

% ---- 解析结果 ----
A_opt_all = zeros(1, Nm);  % 初始化全模式幅度
P_opt_all = zeros(1, Nm);  % 初始化全模式相位
A_opt = x_opt(1:active_Nm);
P_opt = x_opt(active_Nm+1:2*active_Nm);

% 将有效模式参数映射回全模式列表
active_idx = find(valid_modes);
for i = 1:active_Nm
    A_opt_all(active_idx(i)) = A_opt(i);
    P_opt_all(active_idx(i)) = P_opt(i);
end

fprintf('固定波导尺寸：a = %.2f mm, b = %.2f mm\n', a0*1e3, b0*1e3);
for i = 1:Nm
    if valid_modes(i)
        fprintf('%s: 幅度 = %.3f, 相位 = %.3f rad\n', modes{i}, A_opt_all(i), P_opt_all(i));
    else
        fprintf('%s: 无效模式（已过滤）\n', modes{i});
    end
end

% ---- 生成最优远场（使用固定a0和b0）----
[X2, Y2] = meshgrid(linspace(0, a0, Nx), linspace(0, b0, Ny));
E_sum = zeros(size(X2));
for idx = 1:active_Nm
    mode = active_modes{idx};
    [m, n] = parse_mode(mode);
    [Ex, Ey, ~] = TE_field(m, n, X2, Y2, a0, b0);
    E_mode = (Ex + 1j*Ey) * A_opt(idx) * exp(1j*P_opt(idx));
    E_sum = E_sum + E_mode;
end
E_pad = padarray(E_sum, [Ny*(zp-1), Nx*(zp-1)], 0, 'post');
F = fftshift(fft2(E_pad));
F(~mask_propagate) = 0;
E_far_slice = interp2(KX, KY, F, kx_grid, ky_grid, 'spline', 0);
E_far_slice = abs(E_far_slice); E_far_slice = E_far_slice / max(E_far_slice + eps);

% ---- 绘图 ----
figure;
plot(theta, target_far, 'k--', 'LineWidth', 1.5); hold on;
plot(theta, E_far_slice, 'r-', 'LineWidth', 2);
legend('目标远场', '优化结果');
xlabel('\theta (度)'); ylabel('归一化强度'); grid on;
title('远场方向图比较');

% ---- 修改后的子函数 ----
function err = compute_cost_fixed(x, active_modes, X, Y, KX, KY, mask_propagate, kxg, kyg, target_far, zp, k0, a, b)
    active_Nm = numel(active_modes);
    amp = x(1:active_Nm);
    phase = x(active_Nm+1:2*active_Nm);
    [Nx, Ny] = size(X);
    [X2, Y2] = meshgrid(linspace(0, a, Nx), linspace(0, b, Ny));
    E_sum = zeros(size(X2));
    
    % 仅处理有效模式
    for idx = 1:active_Nm
        [m, n] = parse_mode(active_modes{idx});
        [Ex, Ey, ~] = TE_field(m, n, X2, Y2, a, b);
        E_sum = E_sum + (Ex + 1j*Ey) * amp(idx) * exp(1j*phase(idx));
    end
    
    E_pad = padarray(E_sum, [Ny*(zp-1), Nx*(zp-1)], 0, 'post');
    F = fftshift(fft2(E_pad));
    F(~mask_propagate) = 0;
    E_far = interp2(KX, KY, F, kxg, kyg, 'spline', 0);
    E_far = abs(E_far); E_far = E_far / max(E_far + eps);
    err = mean((E_far - target_far).^2);
end

% 原有函数保持不变
function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
    Ex = -1j * (n*pi/b) * cos(m*pi*X/a) .* sin(n*pi*Y/b);
    Ey =  1j * (m*pi/a) * sin(m*pi*X/a) .* cos(n*pi*Y/b);
    norm_factor = max(max(sqrt(abs(Ex).^2 + abs(Ey).^2)));
    Ex = Ex / norm_factor; Ey = Ey / norm_factor;
end

function [m, n] = parse_mode(mode_str)
    tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
    m = str2double(tokens{1}{1});
    n = str2double(tokens{1}{2});
end
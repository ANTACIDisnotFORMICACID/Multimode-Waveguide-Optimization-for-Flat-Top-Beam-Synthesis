%% 优化模块：使用粒子群优化加速反推近场模态组合（平顶方向图）
clear; clc; close all;

% ---- 参数设置 ----
a0 = 20e-3; b0 = 10e-3; f = 30e9;
c = 3e8; lambda = c / f; k0 = 2*pi/lambda; zp = 4;

% 模式列表
modes = {'TE10','TE01','TE11','TE20','TE02','TE21','TE12'};
Nm = numel(modes);

% 空间网格
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
theta = linspace(-30, 30, 61); phi = 0;
kx_grid = k0 * sind(theta) * cosd(phi);
ky_grid = k0 * sind(theta) * sind(phi);

% ---- 目标远场分布：平顶方向图 ----
theta_c = 1; sigma = 2;
target_far = double(abs(theta) <= theta_c) + exp(-((abs(theta) - theta_c).^2) / (2*sigma^2)) .* (abs(theta) > theta_c);
target_far = target_far / max(target_far);

% ---- 优化变量 ----
lb = [zeros(1,Nm), -pi*ones(1,Nm), 5e-3, 5e-3];
ub = [ones(1,Nm), pi*ones(1,Nm), 40e-3, 30e-3];
nvars = 2*Nm + 2;

% 启动并行池
if isempty(gcp('nocreate'))
    parpool;
end

% ---- 粒子群优化配置 ----
opts = optimoptions('particleswarm', ...
    'Display','iter','MaxIterations',300, ...
    'SwarmSize',60, 'UseParallel', true);

% ====== 新增：优化计时 ======
fprintf('优化开始...\n');
tic;
[x_opt, fval] = particleswarm(@(x) compute_cost(x, modes, X, Y, KX, KY, mask_propagate, kx_grid, ky_grid, target_far, zp, k0),...
    nvars, lb, ub, opts);
total_time = toc;
fprintf('优化总耗时：%.2f 秒\n\n', total_time);

% ---- 解析结果 ----
A_opt = x_opt(1:Nm); P_opt = x_opt(Nm+1:2*Nm);
a_opt = x_opt(end-1); b_opt = x_opt(end);

% ====== 新增：模式截止验证 ======
fprintf('优化后波导尺寸：a = %.2f mm, b = %.2f mm\n', a_opt*1e3, b_opt*1e3);
fprintf('工作频率：%.1f GHz\n', f/1e9);

for i = 1:Nm
    [m, n] = parse_mode(modes{i});
    kc = sqrt((m*pi/a_opt)^2 + (n*pi/b_opt)^2);  % 截止波数
    fc = c*kc/(2*pi);                           % 截止频率
    is_cutoff = k0 < kc;                        % 截止判断
    
    

if is_cutoff
        fprintf('%s: 幅度 = %.3f, 相位 = %.3f rad\n', modes{i}, A_opt(i), P_opt(i));
    else
        fprintf('%s: 无效模式（已过滤）\n', modes{i});
end

end

% ---- 生成最优远场（自动过滤截止模式）----
x2 = linspace(0, a_opt, Nx); y2 = linspace(0, b_opt, Ny);
[X2, Y2] = meshgrid(x2, y2);
E_sum = zeros(size(X2));

for idx = 1:Nm
    [m, n] = parse_mode(modes{idx});
    kc2 = (m*pi/a_opt)^2 + (n*pi/b_opt)^2;
    
    % 自动跳过截止模式
    if k0^2 < kc2
        continue;
    end
    
    [Ex, Ey, ~] = TE_field(m, n, X2, Y2, a_opt, b_opt);
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

% ---- 子函数 ----
function err = compute_cost(x, modes, X, Y, KX, KY, mask_propagate, kxg, kyg, target_far, zp, k0)
    Nm = numel(modes); amp = x(1:Nm); phase = x(Nm+1:2*Nm);
    a = x(end-1); b = x(end);
    [Nx, Ny] = size(X);
    [X2, Y2] = meshgrid(linspace(0, a, Nx), linspace(0, b, Ny));
    E_sum = zeros(size(X2));
    for idx = 1:Nm
        [m, n] = parse_mode(modes{idx});
        kc2 = (m*pi/a)^2 + (n*pi/b)^2;
        if k0^2 < kc2, continue; end
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
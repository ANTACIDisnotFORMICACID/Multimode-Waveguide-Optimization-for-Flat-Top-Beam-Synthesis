%% 多模TE矩形波导：近场 & 远场方向图可视化（实数版修正版）
clear; clc; close all;

%% 参数设置
a = 20e-3;      % 波导宽边 (m)
b = 10e-3;      % 波导窄边 (m)
f = 30e9;       % 工作频率30 GHz
c = 3e8;        % 光速
lambda = c/f;   % 波长
k0 = 2*pi/lambda; % 自由空间波数

% 模式设置（TE_mn）及对应振幅和相位（rad）
modes = {
    'TE01', 1.0, 0;
    'TE02', 0.8, 0;
    'TE03', 0.3, 0;
    'TE04', 1.0, 0;
    'TE05', 1.0, 0;
};

%% 网格采样点数（近场分布）
Nx = 512; Ny = 512;
x = linspace(-a/2, a/2, Nx); % 对称坐标
y = linspace(-b/2, b/2, Ny); % 对称坐标
[X, Y] = meshgrid(x, y);

%% 远场角度范围与采样点数 (φ=0对应x轴)
theta_range = linspace(-90, 90, 361);  % 宽角度，细采样
phi_value = 0;  % x轴对应phi=0

figure('Name','远场沿x轴方向强度与相位','NumberTitle','off', 'Position', [100,100,900,600]);
subplot(2,1,1); hold on; grid on;
xlabel('\theta (deg)'); ylabel('远场强度 (线性)');
title('沿 x 轴方向远场强度');
subplot(2,1,2); hold on; grid on;
xlabel('\theta (deg)'); ylabel('远场相位 (rad)');
title('沿 x 轴方向远场相位');

num_modes = size(modes,1);
legend_labels = {};
valid_modes = 0;

for idx = 1:num_modes
    mode_str = modes{idx,1};
    amp = modes{idx,2};
    phase_mode = modes{idx,3};

    [m, n] = parse_mode(mode_str);

    % 截止波数检查
    kc_sq = (m*pi/a)^2 + (n*pi/b)^2;
    if k0^2 < kc_sq
        fprintf('%s 模截止，跳过计算。\n', mode_str);
        continue;
    end

    valid_modes = valid_modes + 1;
    legend_labels{valid_modes} = mode_str;

    % 计算近场（实数表达）
    [Ex, Ey, ~] = TE_field(m, n, X, Y, a, b);

    % 近场复数场：实部为Ex, 虚部为Ey，整体乘振幅和相位
    E_near = (Ex + 1j*Ey) * amp * exp(1j*phase_mode);

    % 计算远场切片
    E_far_slice = calculate_far_field_slice(E_near, X, Y, k0, theta_range, phi_value);

    % 归一化幅度
    E_far_slice_norm = abs(E_far_slice) / max(abs(E_far_slice));
    phase_far_slice = unwrap(angle(E_far_slice));

    % 绘制远场幅度（线性）
    subplot(2,1,1);
    plot(theta_range, E_far_slice_norm, 'LineWidth', 1.5);

    % 绘制远场相位
    subplot(2,1,2);
    plot(theta_range, phase_far_slice, 'LineWidth', 1.5);
end

subplot(2,1,1);
legend(legend_labels, 'Location', 'best');
subplot(2,1,2);
legend(legend_labels, 'Location', 'best');

%% 子函数区
function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
    % 矩形波导TE_mn模式电场（实数版本）
    X_adj = X + a/2;
    Y_adj = Y + b/2;

    Ex = - (n*pi/b) * cos(m*pi*X_adj/a) .* sin(n*pi*Y_adj/b);
    Ey =   (m*pi/a) * sin(m*pi*X_adj/a) .* cos(n*pi*Y_adj/b);

    E_mag = sqrt(Ex.^2 + Ey.^2);
    norm_factor = max(E_mag(:));
    Ex = Ex / norm_factor;
    Ey = Ey / norm_factor;
end

function [m, n] = parse_mode(mode_str)
    % 解析模式字符串，提取m和n
    tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
    m = str2double(tokens{1}{1});
    n = str2double(tokens{1}{2});
end

function E_far_slice = calculate_far_field_slice(E_near, X, Y, k0, theta_range, phi)
    % 远场积分，二维trapz积分
    dx = X(1,2) - X(1,1);
    dy = Y(2,1) - Y(1,1);
    E_far_slice = zeros(size(theta_range));

    for i = 1:length(theta_range)
        theta = theta_range(i);
        u = sind(theta) * cosd(phi);
        v = sind(theta) * sind(phi);
        phase_factor = exp(-1j * k0 * (u * X + v * Y));
        integrand = E_near .* phase_factor;
        % trapz二维积分，先X方向再Y方向
        tmp = trapz(Y(:,1), trapz(X(1,:), integrand, 2));
        E_far_slice(i) = tmp;
    end
end

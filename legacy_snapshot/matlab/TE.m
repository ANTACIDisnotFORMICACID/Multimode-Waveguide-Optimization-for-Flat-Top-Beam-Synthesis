%% 多模TE矩形波导：近场 & 远场方向图可视化（修正版-零点清零）
clear; clc; close all;

%% 参数设置
a = 20e-3;      
b = 10e-3;      
f = 30e9;           % 工作频率30 GHz
c = 3e8;            % 光速
lambda = c/f;       % 波长
k0 = 2*pi/lambda;   % 自由空间波数
zp = 8;             % 零填充倍数，增加FFT分辨率降低泄漏

% 模式设置（TE_mn）及对应振幅和相位（rad）
modes = {
    'TE10', 1.0, 0;
    'TE20', 0.8, pi/4;
    'TE01', 0.7, pi/2;
    'TE11', 0.6, pi/3;
    'TE02', 0.5, pi/2;
    'TE21', 0.4, pi;
};

%% 网格采样点数（近场分布）
Nx = 512; Ny = 512;
x = linspace(0, a, Nx);
y = linspace(0, b, Ny);
[X, Y] = meshgrid(x, y);

%% 波数空间网格，为FFT后远场计算准备
kx = linspace(-k0, k0, zp*Nx);
ky = linspace(-k0, k0, zp*Ny);
[KX, KY] = meshgrid(kx, ky);
mask_propagate = (KX.^2 + KY.^2) <= k0^2;

%% 远场x轴切片设置
theta = linspace(-60, 60, 361);  % 宽角度，细采样
phi = 0;  % x轴对应phi=0度
kx_grid = k0 * sind(theta) * cosd(phi);
ky_grid = k0 * sind(theta) * sind(phi);

figure('Name','远场沿x轴方向强度与相位','NumberTitle','off', 'Position', [100,100,900,500]);
colors = lines(size(modes,1));

for idx = 1:size(modes,1)
    mode_str = modes{idx,1};
    amp = modes{idx,2};
    phase_mode = modes{idx,3};

    [m, n] = parse_mode(mode_str);
    kc_sq = (m*pi/a)^2 + (n*pi/b)^2;
    if k0^2 < kc_sq
        warning('%s 模截止，跳过计算。', mode_str);
        continue;
    end

    % 计算近场
    [Ex, Ey, ~] = TE_field(m, n, X, Y, a, b);
    E_near = (Ex + 1j*Ey) * amp * exp(1j*phase_mode);

    % FFT及零填充
    pad_x = Nx*(zp-1);
    pad_y = Ny*(zp-1);
    E_pad = padarray(E_near, [pad_y, pad_x], 0, 'post');
    F = fftshift(fft2(E_pad));
    F(~mask_propagate) = 0;

    % 插值获取远场切片
    F_interp = griddedInterpolant(KX', KY', F', 'linear', 'none');
    E_far_slice = zeros(size(theta), 'like', F);
    valid = (kx_grid.^2 + ky_grid.^2) <= k0^2;
    E_far_slice(valid) = F_interp(kx_grid(valid), ky_grid(valid));

    % ===== 关键修正：直接将 θ=0 对应点置 0 =====
    [~, zero_idx] = min(abs(theta));
    E_far_slice(zero_idx) = 0;

    % 幅度归一化
    amp_far_slice = abs(E_far_slice);
    max_amp = max(amp_far_slice);
    amp_far_slice_norm = amp_far_slice / max_amp;

    % 相位处理
    phase_far_slice = angle(E_far_slice);
    mainlobe_idx = find(amp_far_slice > 0.01*max_amp);
    if ~isempty(mainlobe_idx)
        mainlobe_phase = phase_far_slice(mainlobe_idx);
        unwrapped_phase = unwrap(mainlobe_phase);
        phase_far_slice(mainlobe_idx) = unwrapped_phase;
    end

    % 绘图
    subplot(2,1,1)
    plot(theta, 20*log10(amp_far_slice_norm + eps), 'DisplayName', mode_str, ...
        'LineWidth', 1.5, 'Color', colors(idx,:))
    hold on

    subplot(2,1,2)
    plot(theta, phase_far_slice, 'DisplayName', mode_str, ...
        'LineWidth', 1.5, 'Color', colors(idx,:))
    hold on
end

% 添加标签与图例
subplot(2,1,1)
xlabel('\theta (deg)')
ylabel('远场强度 (dB)')
title('沿 x 轴方向远场强度')
grid on
ylim([-40, 0])
legend('Location','best')

subplot(2,1,2)
xlabel('\theta (deg)')
ylabel('远场相位 (rad)')
title('沿 x 轴方向远场相位')
grid on
phase_limits = ylim;
new_limits = [min(-pi, phase_limits(1)), max(pi, phase_limits(2))];
ylim(new_limits)

%% --- 子函数区 ---
function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
    Ex = -1j * (n*pi/b) * cos(m*pi*X/a) .* sin(n*pi*Y/b);
    Ey =  1j * (m*pi/a) * sin(m*pi*X/a) .* cos(n*pi*Y/b);
    Ex(isnan(Ex)) = 0;
    Ey(isnan(Ey)) = 0;
    E_mag = sqrt(abs(Ex).^2 + abs(Ey).^2);
    norm_factor = max(E_mag(:));
    if norm_factor > 0
        Ex = Ex / norm_factor;
        Ey = Ey / norm_factor;
    end
end

function [m, n] = parse_mode(mode_str)
    tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
    m = str2double(tokens{1}{1});
    n = str2double(tokens{1}{2});
end

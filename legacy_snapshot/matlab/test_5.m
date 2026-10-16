
E_mag_db_modes = cell(size(modes,1),1);

%% 
%% 多模TE矩形波导：近场 & 远场（kx-ky 方向图）可视化
clear; clc; close all;

%% 参数设置
a = 20e-3;              % 波导宽度 (m)
b = 10e-3;              % 波导高度 (m)
f = 30e9;               % 工作频率 (Hz)
c = 3e8;                % 光速
lambda = c / f;         % 波长
k0 = 2*pi / lambda;     % 自由空间波数
zp = 4;                 % 零填充倍数

% 模式设置：'TEmn', 幅度, 相位
modes = {
    'TE10', 1.0, 0;
    'TE20', 0.8, pi/4;
    'TE01', 0.7, pi/2;
    'TE11', 0.6, pi/3;
};

%% 空间网格
Nx = 128; Ny = 64;
x = linspace(0, a, Nx);
y = linspace(0, b, Ny);
[X, Y] = meshgrid(x, y);

dx = a / (Nx - 1);
dy = b / (Ny - 1);

%% 遍历每个模式，绘制近场和二维远场
for idx = 1:size(modes,1)
    mode_str = modes{idx,1};
    amp = modes{idx,2};
    phase = modes{idx,3};

    % 提取 m, n
    [m, n] = parse_mode(mode_str);

    % 截止判断
    kc_sq = (m*pi/a)^2 + (n*pi/b)^2;
    if k0^2 < kc_sq
        warning('%s 模截止，跳过计算。', mode_str);
        continue;
    end

    % 近场矢量电场（复数）
    [Ex, Ey] = calc_TE_field(m, n, X, Y, a, b, lambda);
    E_mode = (Ex + 1j*Ey) * amp * exp(1j*phase);

    % %% 近场图像
    % figure('Name', [mode_str ' 近场'], 'NumberTitle','off');
    % subplot(1,2,1)
    % imagesc(x*1e3, y*1e3, abs(E_mode));
    % axis xy equal tight;
    % colorbar; xlabel('x (mm)'); ylabel('y (mm)');
    % title([mode_str ' 幅度']);
    % 
    % subplot(1,2,2)
    % imagesc(x*1e3, y*1e3, angle(E_mode));
    % axis xy equal tight;
    % colormap(hsv); clim([-pi pi]);
    % colorbar('Ticks', -pi:pi/2:pi, 'TickLabels', {'-π','-π/2','0','π/2','π'});
    % xlabel('x (mm)'); ylabel('y (mm)');
    % title([mode_str ' 相位']);

    %% 零填充并 FFT（远场）
    E_pad = padarray(E_mode, [(zp-1)*Ny, (zp-1)*Nx], 0, 'post');
    E_fft = fftshift(fft2(E_pad));

    % 空间波数坐标
    kx = linspace(-pi/dx, pi/dx, zp*Nx);
    ky = linspace(-pi/dy, pi/dy, zp*Ny);
    [KX, KY] = meshgrid(kx, ky);

    % 幅度归一化为 dB
    E_mag = abs(E_fft);
    E_mag_db = 20*log10(E_mag / max(E_mag(:)) + eps);
    E_mag_db_modes{idx} = E_mag_db;
    E_all = 0+E_mag_db;

    % %% 远场图像单独（kx-ky 方向图）
    % figure('Name', [mode_str ' 远场方向图'], 'NumberTitle','off');
    % imagesc(kx/k0, ky/k0, E_mag_db);  % 单位归一化为 k0
    % xlabel('k_x / k_0'); ylabel('k_y / k_0');
    % title([mode_str ' 模二维远场方向图 (dB)']);
    % colormap(jet); colorbar;
    % clim([-60 0]);
    % axis xy; axis equal;
end

figure('Name','叠加后的远场','NumberTitle','off','Position',[100,100,1000,800]);
    imagesc(kx/k0, ky/k0, E_all)
    axis xy equal tight
    colormap(jet)
    caxis([-60 0])
    colorbar
    xlabel('k_x / k_0')
    ylabel('k_y / k_0')
    title([modes{idx,1} ' 模远场 (dB)'])

%%总图
figure('Name','2×2 模式远场方向图汇总','NumberTitle','off','Position',[100,100,1000,800]);
for idx = 1:4
    subplot(2,2,idx)
    imagesc(kx/k0, ky/k0, E_mag_db_modes{idx})
    axis xy equal tight
    colormap(jet)
    caxis([-60 0])
    colorbar
    xlabel('k_x / k_0')
    ylabel('k_y / k_0')
    title([modes{idx,1} ' 模远场 (dB)'])
end

%% -------- 子函数 --------
function [m, n] = parse_mode(mode_str)
    tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
    m = str2double(tokens{1}{1});
    n = str2double(tokens{1}{2});
end

function [Ex, Ey] = calc_TE_field(m, n, X, Y, a, b, lambda)
    mu0 = 4*pi*1e-7;
    eps0 = 8.854e-12;
    c = 1/sqrt(mu0*eps0);
    f = c/lambda;
    omega = 2*pi*f;

    kc = pi * sqrt((m/a)^2 + (n/b)^2);
    if kc == 0
        Ex = zeros(size(X)); Ey = Ex;
        return
    end

    coeff = 1j * omega * mu0 / kc^2;

    Ex = -coeff * (n*pi/b) .* cos(m*pi*X/a) .* sin(n*pi*Y/b);
    Ey =  coeff * (m*pi/a) .* sin(m*pi*X/a) .* cos(n*pi*Y/b);
end


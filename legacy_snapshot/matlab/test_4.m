

% %% 多模TE矩形波导：近场 & 远场球面方向图可视化
% clear; clc; close all;
% 
% %% 参数设置
% a = 20e-3;       % 波导宽度 m
% b = 10e-3;       % 波导高度 m
% f = 30e9;        % 工作频率 30 GHz
% c = 3e8;         % 光速 m/s
% lambda = c/f;    % 波长
% k0 = 2*pi/lambda; % 自由空间波数
% zp = 2;          % FFT零填充倍数
% 
% % 模式及其振幅和相位 (rad)
% modes = {
%     'TE10', 1.0, 0;
%     'TE20', 0.8, 0;
%     'TE01', 0.7, 0;
%     'TE02', 0.5, 0;
%     'TE11', 0.6, 0;
%     'TE21', 0.4, 0;
% };
% 
% %% 近场空间网格
% Nx = 128; Ny = 64;
% x = linspace(0, a, Nx);
% y = linspace(0, b, Ny);
% [X, Y] = meshgrid(x, y);
% dx = a / (Nx - 1);
% dy = b / (Ny - 1);
% 
% %% 远场角度网格（球面）
% theta_range = linspace(-90, 90, 181);      % 俯仰角0~180°
% phi_range = linspace(-180, 180, 181);     % 方位角-180~180°
% 
% n_modes = size(modes, 1);
% 
% %% 创建图形和布局（n_modes个子图，最多3列）
% n_cols = 3;
% n_rows = ceil(n_modes / n_cols);
% figure('Name', '多模TE矩形波导远场球面强度分布', 'NumberTitle', 'off', 'Position', [100, 100, 1400, 400*n_rows]);
% tlo = tiledlayout(n_rows, n_cols, 'TileSpacing', 'compact', 'Padding', 'compact');
% 
% %% 计算并绘制每个模式的远场
% for idx = 1:n_modes
%     mode_str = modes{idx, 1};
%     amp = modes{idx, 2};
%     phase_mode = modes{idx, 3};
% 
%     % 解析模号
%     [m, n] = parse_mode(mode_str);
% 
%     % 截止波数判断，若截止跳过
%     kc_sq = (m*pi/a)^2 + (n*pi/b)^2;
%     if k0^2 < kc_sq
%         warning('%s 模截止，跳过。', mode_str);
%         continue;
%     end
% 
%     % 计算近场电场复数分布
%     [Ex, Ey, ~] = TE_field(m, n, X, Y, a, b);
%     E_near = (Ex + 1j*Ey) * amp * exp(1j*phase_mode);
% 
%     % 计算球面远场复场
%     E_far = calculate_far_field_sphere(E_near, X, Y, k0, dx, dy, theta_range, phi_range);
% 
%     % 归一化幅度
%     E_far_norm = abs(E_far) / max(abs(E_far(:)));
% 
%     % 转换为dB，限制动态范围
%     E_far_dB = 20 * log10(E_far_norm + eps);
%     E_far_dB(E_far_dB < -40) = -40;
% 
%     % 切换到下一个子图
%     ax = nexttile(tlo);
% 
%     % 绘制图像，x轴为theta，y轴为phi
%     imagesc(theta_range, phi_range, E_far_dB');
%     set(ax, 'YDir', 'normal'); % y轴正方向向上
%     axis(ax, 'equal');
%     axis(ax, 'tight');
% 
%     xlabel(ax, '\theta (deg)');
%     ylabel(ax, '\phi (deg)');
%     title(ax, [mode_str ' 模远场强度 (dB)']);
%     colormap(ax, jet);
%     colorbar(ax);
%     caxis(ax, [-40 0]); % 动态范围 -40 dB ~ 0 dB
% end
% 
% %% 子函数：解析模式编号
% function [m, n] = parse_mode(mode_str)
%     tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
%     m = str2double(tokens{1}{1});
%     n = str2double(tokens{1}{2});
% end
% 
% %% 子函数：计算TE模式近场电场分布
% function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
%     Ex = -1j * (n*pi/b) * cos(m*pi*X/a) .* sin(n*pi*Y/b);
%     Ey =  1j * (m*pi/a) * sin(m*pi*X/a) .* cos(n*pi*Y/b);
%     norm_factor = max(max(sqrt(abs(Ex).^2 + abs(Ey).^2)));
%     Ex = Ex / norm_factor;
%     Ey = Ey / norm_factor;
% end
% 
% %% 子函数：计算球面远场复场（积分形式）
% function E_far = calculate_far_field_sphere(E_near, X, Y, k0, dx, dy, theta_range, phi_range)
%     E_far = zeros(length(theta_range), length(phi_range));
%     for ti = 1:length(theta_range)
%         theta = theta_range(ti);
%         for pi = 1:length(phi_range)
%             phi = phi_range(pi);
%             u = sind(theta) * cosd(phi);
%             v = sind(theta) * sind(phi);
%             phase_factor = exp(-1j * k0 * (u * X + v * Y));
%             integrand = E_near .* phase_factor;
%             E_far(ti, pi) = sum(integrand(:)) * dx * dy;
%         end
%     end
% end

%% 多模TE矩形波导：近场 & 远场球面方向图可视化
clear; clc; close all;

%% 参数设置
a = 20e-3;       % 波导宽度 m
b = 10e-3;       % 波导高度 m
f = 30e9;        % 工作频率 30 GHz
c = 3e8;         % 光速 m/s
lambda = c/f;    % 波长
k0 = 2*pi/lambda; % 自由空间波数
zp = 2;          % FFT零填充倍数

% 模式及其振幅和相位 (rad)
modes = {
    'TE10', 1.0, 0;
    'TE20', 0.8, 0;
    'TE01', 0.7, 0;
    'TE02', 0.5, 0;
    'TE11', 0.6, 0;
    'TE21', 0.4, 0;
};

%% 近场空间网格
Nx = 128; Ny = 64;
x = linspace(0, a, Nx);
y = linspace(0, b, Ny);
[X, Y] = meshgrid(x, y);
dx = a / (Nx - 1);
dy = b / (Ny - 1);

%% 远场角度网格（球面）——修改为仅上半球面
theta_range = linspace(0, 90, 91);      % 俯仰角0~90°（纵轴）
phi_range = linspace(-180, 180, 181);   % 方位角-180~180°（横轴）

n_modes = size(modes, 1);

%% 创建图形和布局（n_modes个子图，最多3列）
n_cols = 3;
n_rows = ceil(n_modes / n_cols);
figure('Name', '多模TE矩形波导远场球面强度分布', 'NumberTitle', 'off', 'Position', [100, 100, 1400, 400*n_rows]);
tlo = tiledlayout(n_rows, n_cols, 'TileSpacing', 'compact', 'Padding', 'compact');

%% 计算并绘制每个模式的远场
for idx = 1:n_modes
    mode_str = modes{idx, 1};
    amp = modes{idx, 2};
    phase_mode = modes{idx, 3};
    
    % 解析模号
    [m, n] = parse_mode(mode_str);
    
    % 截止波数判断，若截止跳过
    kc_sq = (m*pi/a)^2 + (n*pi/b)^2;
    if k0^2 < kc_sq
        warning('%s 模截止，跳过。', mode_str);
        continue;
    end
    
    % 计算近场电场复数分布
    [Ex, Ey, ~] = TE_field(m, n, X, Y, a, b);
    E_near = (Ex + 1j*Ey) * amp * exp(1j*phase_mode);
    
    % 计算球面远场复场
    E_far = calculate_far_field_sphere(E_near, X, Y, k0, dx, dy, theta_range, phi_range);
    
    % 归一化幅度
    E_far_norm = abs(E_far) / max(abs(E_far(:)));
    
    % 转换为dB，限制动态范围
    E_far_dB = 20 * log10(E_far_norm + eps);
    E_far_dB(E_far_dB < -40) = -40;
    
    % 切换到下一个子图
    ax = nexttile(tlo);
    
    % 修改：交换坐标轴，theta为纵轴，phi为横轴
    imagesc(phi_range, theta_range, E_far_dB);  % phi_range为横轴，theta_range为纵轴
    set(ax, 'YDir', 'normal'); % y轴正方向向上（θ从0°到90°向上增加）
    
    % 设置坐标轴标签
    xlabel(ax, '\phi (deg)');  % 横轴为方位角φ
    ylabel(ax, '\theta (deg)'); % 纵轴为俯仰角θ
    title(ax, [mode_str ' 模远场强度 (dB)']);
    colormap(ax, jet);
    colorbar(ax);
    caxis(ax, [-40 0]); % 动态范围 -40 dB ~ 0 dB
    
    % 设置坐标轴范围
    xlim(ax, [-180, 180]);
    ylim(ax, [0, 90]);
end

%% 子函数：解析模式编号
function [m, n] = parse_mode(mode_str)
    tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
    m = str2double(tokens{1}{1});
    n = str2double(tokens{1}{2});
end

%% 子函数：计算TE模式近场电场分布
function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
    Ex = -1j * (n*pi/b) * cos(m*pi*X/a) .* sin(n*pi*Y/b);
    Ey =  1j * (m*pi/a) * sin(m*pi*X/a) .* cos(n*pi*Y/b);
    norm_factor = max(max(sqrt(abs(Ex).^2 + abs(Ey).^2)));
    Ex = Ex / norm_factor;
    Ey = Ey / norm_factor;
end

%% 子函数：计算球面远场复场（积分形式）
function E_far = calculate_far_field_sphere(E_near, X, Y, k0, dx, dy, theta_range, phi_range)
    E_far = zeros(length(theta_range), length(phi_range));
    for ti = 1:length(theta_range)
        theta = theta_range(ti);
        for pi = 1:length(phi_range)
            phi = phi_range(pi);
            u = sind(theta) * cosd(phi);
            v = sind(theta) * sind(phi);
            phase_factor = exp(-1j * k0 * (u * X + v * Y));
            integrand = E_near .* phase_factor;
            E_far(ti, pi) = sum(integrand(:)) * dx * dy;
        end
    end
end
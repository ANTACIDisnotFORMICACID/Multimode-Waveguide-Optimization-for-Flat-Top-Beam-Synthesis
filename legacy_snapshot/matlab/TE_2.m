% %% 多模TE矩形波导：近场 & 远场方向图可视化（虚数版）
% clear; clc; close all;
% 
% %% 参数设置
% a = 20e-3;      % 波导宽边
% b = 10e-3;      % 波导窄边
% f = 30e9;       % 工作频率30 GHz
% c = 3e8;        % 光速
% lambda = c/f;   % 波长
% k0 = 2*pi/lambda; % 自由空间波数
% 
% % 模式设置（TE_mn）及对应振幅和相位（rad）
% modes = {
%     'TE10', 1.0, 0;
%     'TE20', 0.8, pi/4;
%     % 'TE01', 0.7, pi/2;
%     % 'TE11', 0.6, pi/3;
%     % 'TE02', 0.5, pi/2;
%     % 'TE21', 0.4, pi;
%     'TE30', 0.3, 0;
%     'TE40',1.0,0;
%     'TE50',1.0,0;
% };
% 
% %% 网格采样点数（近场分布）
% Nx = 512; Ny = 512;
% x = linspace(-a/2, a/2, Nx); % 对称坐标
% y = linspace(-b/2, b/2, Ny); % 对称坐标
% [X, Y] = meshgrid(x, y);
% dx = a/(Nx-1); 
% dy = b/(Ny-1);
% 
% %% 预绘图设置
% figure('Name','远场沿x轴方向强度与相位','NumberTitle','off', 'Position', [100,100,900,600]);
% subplot(2,1,1); hold on; grid on;
% xlabel('\theta (deg)'); ylabel('远场强度 (dB)'); title('沿 x 轴方向远场强度');
% subplot(2,1,2); hold on; grid on;
% xlabel('\theta (deg)'); ylabel('远场相位 (rad)'); title('沿 x 轴方向远场相位');
% 
% % 远场theta角范围与采样点数 (φ=0对应x轴)
% theta_range = linspace(-90, 90, 361);  % 宽角度，细采样
% phi_value = 0;  % x轴对应phi=0
% 
% num_modes = size(modes,1);
% legend_labels = cell(num_modes, 1);
% valid_modes = 0;
% 
% for idx = 1:size(modes,1)
%     mode_str = modes{idx,1};
%     amp = modes{idx,2};
%     phase_mode = modes{idx,3};
% 
%     % 解析模序(m,n)
%     [m, n] = parse_mode(mode_str);
% 
%     % 截止波数检查
%     kc_sq = (m*pi/a)^2 + (n*pi/b)^2;
%     if k0^2 < kc_sq
%         warning('%s 模截止，跳过计算。', mode_str);
%         continue;
%     end
%     valid_modes = valid_modes + 1;
%     legend_labels{valid_modes} = mode_str;
% 
%     % 计算近场
%     [Ex, Ey, ~] = TE_field(m, n, X, Y, a, b);
%     E_near = (Ex + 1j*Ey) * amp * exp(1j*phase_mode);
% 
%     % 使用普适积分函数计算远场x轴切片 (φ=0)
%     [E_far_slice, ~] = calculate_far_field_slice(E_near, X, Y, k0, dx, dy, theta_range, phi_value);
% 
%     % 归一化幅度
%     E_far_slice_norm = abs(E_far_slice) / max(abs(E_far_slice));
% 
%     % 相位处理（解卷绕）
%     phase_far_slice = unwrap(angle(E_far_slice));
% 
%     % 绘制远场幅度曲线
%     subplot(2,1,1)
%     plot(theta_range, 20*log10(E_far_slice_norm + eps), 'LineWidth', 1.5)
%     axis([-90 90 -100 0])
% 
%     % 绘制远场相位曲线
%     subplot(2,1,2)
%     plot(theta_range, 20*log10(E_far_slice_norm + eps), 'LineWidth', 1.5)
%     axis([-90 90 -30 0])
% end
% 
% % 添加图例
% subplot(2,1,1)
% legend(legend_labels(1:valid_modes), 'Location', 'best');
% subplot(2,1,2)
% legend(legend_labels(1:valid_modes), 'Location', 'best');
% 
% %% 近场可视化
% figure('Name','TE模式近场分布','Position',[300,400,1200,800]);
% for idx = 1:valid_modes
%     mode_str = legend_labels{idx};
%     [m, n] = parse_mode(mode_str);
% 
%     subplot(2, valid_modes, idx);
%     [Ex, Ey, ~] = TE_field(m, n, X, Y, a, b);
%     imagesc(x*1000, y*1000, abs(Ex + 1j*Ey));
%     axis equal tight; colorbar;
%     xlabel('x (mm)'); ylabel('y (mm)');
%     title([mode_str ' 场强幅度']);
% 
%     subplot(2, valid_modes, idx+valid_modes);
%     imagesc(x*1000, y*1000, angle(Ex + 1j*Ey));
%     axis equal tight; colorbar;
%     xlabel('x (mm)'); ylabel('y (mm)');
%     title([mode_str ' 场强相位']);
% end
% 
% % --- 子函数区 ---
% function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
%     % 计算矩形波导TE_mn模式的电场分布 (归一化)
%     % 调整坐标到波导内部[0,a]×[0,b]
%     X_adj = X + a/2;
%     Y_adj = Y + b/2;
% 
%     Ex = -1j * (n*pi/b) * cos(m*pi*X_adj/a) .* sin(n*pi*Y_adj/b);
%     Ey =  1j * (m*pi/a) * sin(m*pi*X_adj/a) .* cos(n*pi*Y_adj/b);
% 
%     % 归一化因子：最大电场幅度
%     E_mag = sqrt(abs(Ex).^2 + abs(Ey).^2);
%     norm_factor = max(E_mag(:));
%     Ex = Ex / norm_factor;
%     Ey = Ey / norm_factor;
% end
% 
% function [m, n] = parse_mode(mode_str)
%     % 解析模式字符串，提取m和n
%     tokens = regexp(mode_str, 'TE(\d)(\d)', 'tokens');
%     m = str2double(tokens{1}{1});
%     n = str2double(tokens{1}{2});
% end
% 
% function [E_far_slice, theta] = calculate_far_field_slice(E_near, X, Y, k0, dx, dy, theta_range, phi)
%     % 普适的远场切片计算函数
%     % 输入:
%     %   E_near: 近场分布矩阵 (Ny x Nx)
%     %   X, Y: 网格坐标矩阵 (Ny x Nx)
%     %   k0: 自由空间波数 [rad/m]
%     %   dx, dy: 空间步长
%     %   theta_range: 俯仰角范围 (度)
%     %   phi: 固定方位角 (度)
%     %
%     % 输出:
%     %   E_far_slice: 复数远场切片
%     %   theta: 角度向量 (度)
% 
%     E_far_slice = zeros(size(theta_range));
% 
%     for i = 1:length(theta_range)
%         theta = theta_range(i);
% 
%         % 计算方向余弦
%         u = sind(theta) * cosd(phi);  % x方向方向余弦
%         v = sind(theta) * sind(phi);  % y方向方向余弦
% 
%         % 计算相位因子 (夫琅禾费衍射积分)
%         phase_factor = exp(-1j * k0 * (u * X + v * Y));
% 
%         % 数值积分
%         integrand = E_near .* phase_factor;
%         E_far_slice(i) = sum(integrand(:)) * dx * dy;
%     end
% 
%     theta = theta_range;
% end

%% 多模TE矩形波导：近场 & 远场方向图可视化（虚数版）
clear; clc; close all;

%% 参数设置
a = 20e-3;      % 波导宽边
b = 10e-3;      % 波导窄边
f = 75e9;       % 工作频率30 GHz
c = 3e8;        % 光速
lambda = c/f;   % 波长
k0 = 2*pi/lambda; % 自由空间波数

% 模式设置（TE_mn）及对应振幅和相位（rad）
modes = {
    'TE11', 1.0, 0; 
    'TE21', 0.8, 0;
    'TE31', 1.0, 0;
    'TE41', 1.0, 0;
};

%% 网格采样点数（近场分布）
Nx = 1024; Ny = 512;
x = linspace(-a/2, a/2, Nx); % 对称坐标
y = linspace(-b/2, b/2, Ny); % 对称坐标
[X, Y] = meshgrid(x, y);
dx = a/(Nx-1); 
dy = b/(Ny-1);

%% 预绘图设置：远场沿x轴方向强度与相位
figure('Name','远场沿x轴方向强度与相位','NumberTitle','off', 'Position', [100,100,900,300]);
subplot(1,1,1); hold on; grid on;
xlabel('\theta (deg)'); ylabel('远场强度 (dB)'); title('沿 x 轴方向远场强度');
% subplot(2,1,2); hold on; grid on;
% xlabel('\theta (deg)'); ylabel('远场相位 (pi)'); title('沿 x 轴方向远场相位');

% 远场theta角范围与采样点数 (φ=0对应x轴)
theta_range = linspace(-90, 90, 361);  % 宽角度，细采样
phi_value = 0;  % x轴对应phi=0

num_modes = size(modes,1);
valid_modes = 0;
legend_labels = cell(num_modes, 1);

for idx = 1:size(modes,1)
    mode_str = modes{idx,1};
    amp = modes{idx,2};
    phase_mode = modes{idx,3};

    % 解析模序(m,n)
    [m, n] = parse_mode(mode_str);

    % 截止波数检查
    kc_sq = (m*pi/a)^2 + (n*pi/b)^2;
    fprintf('%s 模式: 截止波数 kc=%.2f, 工作波数 k0=%.2f\n', mode_str, sqrt(kc_sq), k0);
    if k0^2 < kc_sq
        fprintf('%s 模截止，跳过计算。\n', mode_str);
        continue;
    end
    
    valid_modes = valid_modes + 1;
    legend_labels{valid_modes} = mode_str;

    % 计算近场
    [Ex, Ey, ~] = TE_field(m, n, X, Y, a, b);
    E_near = (Ex + 1j*Ey) * amp * exp(1j*phase_mode);

    % 使用普适积分函数计算远场x轴切片 (φ=0)
    [E_far_slice, ~] = calculate_far_field_slice(E_near, X, Y, k0, dx, dy, theta_range, phi_value);

    % 归一化幅度
    E_far_slice_norm = abs(E_far_slice) / max(abs(E_far_slice));

    % 相位处理（解卷绕）
    phase_far_slice = unwrap(angle(E_far_slice));

    % 绘制远场幅度曲线
    subplot(1,1,1)
    plot(theta_range, 20*log10(E_far_slice_norm + eps), 'LineWidth', 3-0.6*idx)
    axis([-90 90 -30 0])

    % 绘制远场相位曲线
    % subplot(2,1,2)
    % plot(theta_range, phase_far_slice/pi, 'LineWidth', 1.5)
end

% 添加图例
subplot(1,1,1)
legend(legend_labels(1:valid_modes), 'Location', 'best');
% subplot(2,1,2)
% legend(legend_labels(1:valid_modes), 'Location', 'best');



%% 子函数区
function [Ex, Ey, norm_factor] = TE_field(m, n, X, Y, a, b)
    % 计算矩形波导TE_mn模式的电场分布 (归一化)
    % 调整坐标到波导内部[0,a]×[0,b]
    X_adj = X + a/2;
    Y_adj = Y + b/2;
    
    Ex = -1j * (n*pi/b) * cos(m*pi*X_adj/a) .* sin(n*pi*Y_adj/b);
    Ey =  1j * (m*pi/a) * sin(m*pi*X_adj/a) .* cos(n*pi*Y_adj/b);

    % 归一化因子：最大电场幅度
    E_mag = sqrt(abs(Ex).^2 + abs(Ey).^2);
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

function [E_far_slice, theta] = calculate_far_field_slice(E_near, X, Y, k0, dx, dy, theta_range, phi)
    % 普适的远场切片计算函数
    % 输入:
    %   E_near: 近场分布矩阵 (Ny x Nx)
    %   X, Y: 网格坐标矩阵 (Ny x Nx)
    %   k0: 自由空间波数 [rad/m]
    %   dx, dy: 空间步长
    %   theta_range: 俯仰角范围 (度)
    %   phi: 固定方位角 (度)
    %
    % 输出:
    %   E_far_slice: 复数远场切片
    %   theta: 角度向量 (度)
    
    E_far_slice = zeros(size(theta_range));
    
    for i = 1:length(theta_range)
        theta = theta_range(i);
        
        % 计算方向余弦
        u = sind(theta) * cosd(phi);  % x方向方向余弦
        v = sind(theta) * sind(phi);  % y方向方向余弦
        
        % 计算相位因子 (夫琅禾费衍射积分)
        phase_factor = exp(-1j * k0 * (u * X + v * Y));
        
        % 数值积分
        integrand = E_near .* phase_factor;
        E_far_slice(i) = sum(integrand(:)) * dx * dy;
    end
    
    theta = theta_range;
end

function [x,r,M,A] = angelino_nozzle_contour(A_t,epsilon, r_e,gamma,points)
% calculates contour of an aerospike engine using Angelino's method

% given the exit radius, r_e, end of plug radius, r_b, desired exit mach
% number, M_e, ratio of specific heats, gamma, and the number of contour
% points to be approximated

% returns length (x) and radius (r) pairs that define the axisymmetric
% nozzle contour. Also returns the mach number vector used to define
% contour. Note, this method assumes the nozzle lip is located at (0,0)

% estimating contour
A_e = A_t.*epsilon;


r_b = sqrt(-A_e./pi + r_e.^2);

[M_e,f_dummy] = fsolve(@(M) mach_expansion_ratio(M,gamma,epsilon),2);

M = linspace(1,M_e,points);

A = A_t.*expansion_ratio(M,gamma);

alpha = prandtl_meyer(M_e,gamma) - prandtl_meyer(M,gamma) + mach_angle(M);
l = (r_e-sqrt(abs(r_e.^2 - (A.*M.*sin(alpha)./pi))))./sin(alpha); %abs is here to prevent complex numbers due to floating point error
x = l.*cos(alpha);
r = l.*sin(alpha);

end
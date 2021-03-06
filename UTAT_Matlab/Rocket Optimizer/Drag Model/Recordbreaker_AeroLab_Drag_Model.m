% Recordbreaker_AeroLab_Drag_Model.m
%
% author: Andreas Marquis
% Date: Winter 2017
%
% Description: This program estimates the drag on a rocket. Based off the
% the drag estimation software: AeroLab 1.3.2.
% 
%           By Andreas Marquis
%
%
%Aerolab is based on the following litterature:
% 
% USAF Stability and control DATCOM
%         Flight Control Division
%         Air Force Flight Dynamics Laboratory
%         Wright-Patterson Air Force Base, Ohio
%         1978
% 
% Boundary Layer Theory
%         Dr. H Schlichting
%         McGraw-Hill
% 
% Mechanics of Fluids
%         W. J. Duncan, A .S Thom, A. D. Young
%         Edward Arnold 
% 
% Missile Configuration Design
%         S. S. Chin
%         McGraw-Hill 1961
% 
% NACA Tecnical Note 1032
% NACA Technical Note 4201
% NACA Tecnical Report 1386
% NACA Tecnical Report 1153
% NACA Tecnical Report 1353
% NACA Tecnical Report 1374
% NACA Tecnical Report 1253
% NACA Tecnical Report 1227
% NACA Tecnical Report 1238
% NACA Tecnical Report 1307
% NACA Research Memorandum RM A53A30
% 
% Nasa Nike Tomahawk Handbook
%         Thiokol Chemical Corporation
%         Astro-Met Division
%         P.O.Box 1497 Ogden, Utah
%         1966
% 
% Stabilisering af raketter ved Hj�lp af Barrowmans metode
%         J. Franck
%         Dansk Amat�r Raket Klub
% 
% Theory of Wing Sections
%         Ira h. Abbot, A. E. Von Doenhoff
%         Dover Publications, Inc 1958
% 
% MIL-HDBK-762(MI): DESIGN OF AERODYNAMICALLY STABILIZED FREE ROCKETS
% 
% All values of the atmospheric parameters are from the US STANDARD ATMOSPHERE 
% SUPPLEMENTS, 1966 (60deg N, July)
%
% History
%-------------------
% 01-15-17 Created by AM

function [  Drag_Model ] = Recordbreaker_AeroLab_Drag_Model(nps)

Drag_Model = NaN(101,9);

addpath('Drag Model\Record Breaker drag values');
dat = zeros(101,9);
addpath('Drag Model\Record Breaker drag values');

if nps == 5
    dat = xlsread('Record-Breaker-Variable-Cd','NPS 5');
end

if nps == 6
    dat = xlsread('Record-Breaker-Variable-Cd','NPS 6');
end

if nps == 8
    dat = xlsread('Record-Breaker-Variable-Cd','NPS 8');
end

%% Original Length
Drag_Model(1:end,1) = dat(1:end,1); %importing mach numbers 
Drag_Model(1:end,2) = dat(1:end,2); %importing unpowered drag @ ground level AND original length
Drag_Model(1:end,3) = dat(1:end,3); %importing powered drag @ ground level AND original length
Drag_Model(1:end,4) = dat(1:end,4); %importing unpowered drag @ 65k level AND original length
Drag_Model(1:end,5) = dat(1:end,5); %importing powered drag @ 65k level AND original length
%% 1.5 x Original Length
Drag_Model(1:end,6) = dat(1:end,6); %importing unpowered drag @ ground level AND 1.5 x original length
Drag_Model(1:end,7) = dat(1:end,7); %importing powered drag @ ground level AND 1.5 x original length
Drag_Model(1:end,8) = dat(1:end,8); %importing unpowered drag @ 65k level AND 1.5 x original length
Drag_Model(1:end,9) = dat(1:end,9); %importing powered drag @ 65k level AND 1.5 x original length


end

close all
clear all
clc

load FMT.mat
load grid.mat
[nxc nyc nzc] = size(hFacC);
xc  = XC(:,1);yc = YC(1,:);zc = RC;
%% te record from 20070101 to  20190930, daily records
nt = 4656;

%% old packing
time = rdslice(['TIME_CCS_2007_2019.bin'],[nt 1],1, fmt, Ieee);

for it = [1 nt]
    t =  rdslice([ 'T_MIT_CCS_2007_2019_fulldomain.bin'],[nxc nyc nzc],it, fmt, Ieee);
    s =  rdslice([ 'S_MIT_CCS_2007_2019_fulldomain.bin'],[nxc nyc nzc],it, fmt, Ieee);
    u =  rdslice([ 'U_MIT_CCS_2007_2019_fulldomain.bin'],[nxc nyc nzc],it, fmt, Ieee);
    v =  rdslice([ 'V_MIT_CCS_2007_2019_fulldomain.bin'],[nxc nyc nzc],it, fmt, Ieee);
    eta = rdslice([ 'Eta_MIT_CCS_2007_2019_fulldomain.bin'],[nxc nyc],it, fmt, Ieee);
    
    figure
    subplot(2,3,1);imagesc(xc,yc,t(:,:,1)');title(['T : ' datestr(time(it))]);colorbar;set(gca,'YDir','normal')
    subplot(2,3,2);imagesc(xc,yc,s(:,:,1)');title(['S : ' datestr(time(it))]);colorbar;set(gca,'YDir','normal')
    subplot(2,3,3);imagesc(xc,yc,u(:,:,1)');title(['U : ' datestr(time(it))]);colorbar;set(gca,'YDir','normal')
    subplot(2,3,4);imagesc(xc,yc,v(:,:,1)');title(['V : ' datestr(time(it))]);colorbar;set(gca,'YDir','normal')
    subplot(2,3,5);imagesc(xc,yc,eta');title(['Eta : ' datestr(time(it))]);colorbar;set(gca,'YDir','normal')
    
end


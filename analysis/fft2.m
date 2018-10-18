clear all % ������� ������
close all;
opengl('save','hardware');

[FileName,PathName,FilterIndex] = uigetfile({'*.txt','Data-files (*.txt)'}, ...
  'Input file with data for analyzer');
if FilterIndex==0
  return 
end

Col=8;
data=textread([PathName,FileName],'%s','delimiter','\t');
for i=1:6
    TitleS(i)=data(10+i);
end
data=data(25:end); %�������� ������ � ��������� ������ �����
dataLength=length(data)/Col;
data=reshape(data,Col,dataLength); %������������ ������ � ������� ������� �������
rez=str2double(data);% ��������� � ������ ������

CurrTitle = strcat(['File: ' FileName ]);
hf=figure('name',CurrTitle,'NumberTitle', 'off','MenuBar','none','NumberTitle', 'off');

%% ���������
t=0.00025;
Tm=t*(dataLength-1);% ����� ������� (�)
Fd=1/t;% ������� ������������� (��)
FftL=4*4096;% ���������� ����� ����� �������
T=0:1/Fd:Tm;% ������ �������� �������

for i=1:4
Signal=rez(i+1,:);
%% ������������ ������������� �������
FftS=abs(fft(Signal,FftL));% ��������� �������������� ����� �������
FftS=(FftL/dataLength)*2*FftS./FftL;% ���������� ������� �� ���������
FftS(1)=FftS(1)/2;% ���������� ���������� ������������ � �������
%% ���������� ��������
hS=subplot(4,2,2*i-1);% ����� ������� ���� ��� ����������
plot(T,Signal,'color','r');% ���������� �������
xlim([0,Tm]);
set(hS,'XGrid', 'on', 'YGrid', 'on', 'GridLineStyle', '-');
set(hS,'XMinorGrid','on','YMinorGrid','on','MinorGridLineStyle',':');
CurrTitle = strcat(['Signal ' TitleS{i}]);
title(CurrTitle);% ������� �������
xlabel('Time (S)','FontName','Arial Cyr','FontSize',30);% ������� ��� � �������
ylabel('Amplitude (V)','FontName','Arial Cyr','FontSize',10);% ������� ��� � �������
hF=subplot(4,2,2*i);% ����� ������� ���� ��� ����������
F=0:Fd/FftL:Fd/2-1/FftL;% ������ ������ ������������ ������� �����
plot(F,FftS(1:length(F)));% ���������� ������� ����� �������
xlim([0,500]);
set(hF,'XGrid', 'on', 'YGrid', 'on', 'GridLineStyle', '-');
set(hF,'XMinorGrid','on','YMinorGrid','on','MinorGridLineStyle',':');
CurrTitle = strcat(['Spectrum ' TitleS{i}]);
title(CurrTitle);% ������� �������
xlabel('Frequency (Hz)','FontName','Arial Cyr','FontSize',10);% ������� ��� � �������
ylabel('Amplitude','FontName','Arial Cyr','FontSize',10);% ������� ��� � �������
end;
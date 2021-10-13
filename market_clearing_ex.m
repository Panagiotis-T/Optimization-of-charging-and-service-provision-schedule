clear all;
close all;
clc;

A = xlsread('filename.xls'); %consumption prognosis, hourly
B = xlsread('filename.xls'); %power supply dk prognosis, hourly
time = 1:744;
p = [];
q = [];
for j=1:744

    SWE(j) = 150; %import from sweden
    GER(j) = 100; %import from germany
    NOR(j) = 200; %import from norway

end

f = [0,-17,70,64,153,82,89,25,0,-25,19,43,39,36,31,5,10,0,1000,1000]; %coeff. vector
D_DK1 = A(1:744,4); %consumption for DK1
D_DK2 = A(1:744,5); %consumption for DK2

S_DK1 = B(1:744,3:10); %supply prognosis dk1
S_DK2 = B(1:744,11:19); %supply prognosis dk2

S = [S_DK1,S_DK2];

S(:,18) = 600; %set available transmission capacity between dk1 and dk2

for i = 1:744
    
   if mod(i,24) < 5 || mod(i,24) > 22
       
       S(i,8) = 0;
       S(i,11) = 0;
       
   end
    
    if mod(i,24) < 7 || mod(i,24) > 14
        
        GER(i) = 0;
        
    end
    
    if mod(i,24) < 16 || mod(i,24) > 19
        
        SWE(i) = 0;
        
    end
    
    D_DK1(i) = D_DK1(i) + GER(i) - NOR(i);
   
    D_DK2(i) = D_DK2(i) + SWE(i);

dd1 = D_DK1(i);

dd2 = D_DK2(i);

S(i,19)= dd1;

S(i,20)=dd2;

Snew = S';

ub = Snew(:,i);

lb = [zeros(1,17),-600,0,0];

Aeq = zeros(2,20);

%When the cable has negative prices the flow is from DK2 to DK1 and vice
%versa
Aeq(1,[1:8,18,19])= [1,1,1,1,1,1,1,1,-1,1];  %constraints
%
Aeq(2,[9:17,18,20])=[1,1,1,1,1,1,1,1,1,1,1];

beq = [D_DK1(i), D_DK2(i)];

[x,fval,exitflag,output,lambda] = linprog(f,[],[],Aeq,beq,lb,ub); %linear prog. solver

% hourly market clearing price
p = [p -1*lambda.eqlin];
% hourly energy produced
q = [q x];

% revenues DK1

for k = 1:8
 revenuesDK1(k,i)=  p(1,i).*q(k,i);
 if k==2
   % Feed-in-Premium
     revenuesDK1(k,i)= p(1,i).*q(k,i)+ 17.*q(k,i);
 end
end
for l =1:9
 revenuesDK2(l,i)=  p(2,i).*q(l+8,i);
 if l==2
   % Feed-in-Tariff
     revenuesDK2(l,i)=  25.*q(l+8,i);
 end
 
end

end

%Overall revenues for each market participant at DK West
revenuesDK1_total = sum(revenuesDK1);

%Overall revenues for each market participant at DK East
revenuesDK2_total = sum(revenuesDK2);


p1=reshape(p(1,:),24,31);
p2=reshape(p(2,:),24,31);

for i=1:24   
%Maximum,Minimum,Average electricity prices for West
avep1(i)=sum(p1(i,:))./31;
maxp1(i)=max(p1(i,:));
minp1(i)=min(p1(i,:));
average1=mean(avep1);
maximum1=max(maxp1);
minimum1=min(minp1);
%Maximum,Minimum,Average electricity prices for East
avep2(i)=sum(p2(i,:))./31;
maxp2(i)=max(p2(i,:));
minp2(i)=min(p2(i,:));
average2=mean(avep2);
maximum2=max(maxp2);
minimum2=min(minp2);
end
%DK1
figure()
hold on
plot(avep1,'Color','r','LineWidth',2)
plot(maxp1,'Color','g','LineWidth',2)
plot(minp1,'Color','b','LineWidth',2)
title('Average, Max and Min Monthly Hourly Prices in DK1')
xlabel('Time (h)')
ylabel('Prices (euro)')
legend('Ave. Elec.price','Max. Elec.price','Min. Elec.price','Location','best')
axis([0 24 -20 95])
set(gca,'fontsize',9,'Xtick',0:2:24)
set(gca,'FontWeight','bold')
hold off
grid on

%DK2
figure()
hold on
plot(avep2,'Color','r','LineWidth',2)
plot(maxp2,'Color','g','LineWidth',2)
plot(minp2,'Color','b','LineWidth',2)
title('Average, Max and Min Monthly Hourly Prices in DK2')
xlabel('Time (h)')
ylabel('Prices (euro)')
legend('Ave. Elec.price','Max. Elec.price','Min. Elec.price','Location','best')
axis([0 24 -20 45])
set(gca,'fontsize',9,'Xtick',0:2:24)
set(gca,'FontWeight','bold')
hold off
grid on
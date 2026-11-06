#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale Zarek Projectile-Destroy-Only Installer

Standalone updater: only destroying projectiles by melee builds Zarek Clash Momentum.
Also includes the earlier Ember/Zarek fixes if not installed; preserves other balance edits.
Includes the earlier clash update when it is not already installed.
No third-party packages, zip files, or network required.

Run from your game folder:
    python Install_Ember_Zarek_Update.py
Or supply your game path:
    python Install_Ember_Zarek_Update.py "C:\\path\\to\\your\\game"

If run outside the game folder, a folder picker opens when tkinter is available.
Creates timestamped backups in .clash_backups before installing.
"""
import argparse
import base64
import datetime
import json
import os
import sys
import tempfile
import zlib
from pathlib import Path

# The original-to-updated code changes are built directly into this installer.
# Data is compressed to keep the standalone file small.
PATCH_DATA = (
    'c-rk->vG&SvVIkKwkpf<j%kv^+sLuEBwMk)u`VUa@#e@X6-a_Jj5s7iawJb2RqaFU6P_nI-2g8jhq~CCWaH%chdd;KMx)XFbvMxXI4W}g@ti',
    'Ih|D%@0XzSx>u}UuB$LYsW93^bDrB6m43)38ajvhZId%JITch3)x4*s$G{N(kU-Sgwaqu2W<=ilk)`v>1?_WJ}H?e6XD9-Y6~-rIh;dw#V2;',
    '`Q6(^ZnhUZ_d9n&JE45b-mN@<<Y_0{TJu2w*P1Q=*9W=Yl+xsGNNJ0axwV3-R;AJ{qyGs`zPDaPtKpe**<=SG<jq4zyJC-xr~a)iy6uC^atj',
    'b5&Wb{Kv=?-YvRYWSdeI$QNJuE1SUmTR4!OfiYQ>5q2GFX*OOY#Gsl)BP53{b7L2?f70dL3y&r9n@Po>KE0<G+o@!^~38AO@+4u?Zaz-znyi',
    'Yp)(%h?hdC~kJ_wL!PKrykR9#A~pvoFo_^s4U4AC730^g82Tga4i0NQf;xme+*D!yuKL`sb;CQFrIR@9HgS+LtPPuHQSWyeO;g?Tb&6-50!w',
    'tv%_sIbcv}Qj~;}rzBKq*^URcdXU6x0>H4MG5!}_GO}bbV<gN091CD6AyEPf;<K!j@CAS*VV8g*87&IzHDA#@P;1IjNEE7;>x_{HPoKh^IMM',
    'eb^7GH+fx@{sT;Ob<!dD&NhH9D9C<b{&Wf>*&@fg{LUn}-RrdlqdLT&kY2S^qr$5+rp2|+M`Z+W_$kW9_e0{<(bpBT{kSkoYcQwXCZDi(Xl)',
    'nP+S$)NlAN!v7M<tk4|nM+JuiyzlRw(|#(vzQ0I23BD<pC$9os#UZ;WgR9p1D~)UvK?5no*gvW<A-ywt5^sH@grhMDP%Sz%W*YoH6Z#=MMx+',
    'kY1kJ|A<Yp-%+w%F7}CyEaMQ5<TorJAGF%?<rDSx;*$Mg2&(-~A1-i<APmSk-gg^LSmPePglp~7HXj|l)Xube-g<-eIb_wfrA=F@toV+^P-B',
    'rJXUTHp^kTTtPg=}q+WQEW;-XdNKivjvy$*s~phStDMDNoZ9XB3rDngF_kJe9FZgFs2xRhPD+O^B}Q#)N3&dRl@WEZY@W4iMbzv`5PY$SP5)',
    'vGTN}e5^GfE>Ps({j?bP-W>$+*k8a9yu*@yP&C!HKt!te086c_mNnk=yI;0$ellJR>gh0Gd@4%FO8ofYLvqCBQve-S<8PJ%(vmdc?}{q~+%Q',
    'IU29PZm@RpYR(-osxTETJwV-_lT`1rRrj?P!|Gkl2SKbNJ*pzgRE!3}Cl5CO?&716(uMVd!Hp<2X8X*#5^;E=Z=FG`C}%7i}HV`LGPe6fUjK',
    '#KH)AbrYp23+-W1%pAms8%3YbV75#<CH6oU{)si>MK&vWfn6qw^FIZJ0_3i$!nTE;lqr{*U(FI2e{sJewFL1K7=$b#Frk3-(Wslq<w<HS;&%',
    'r<&E|>V9`QF4{j>_cq+5h#{zESwJKI^giU|Q6bSq?nq#or*m28<8mH-nI*-$<2{FJh?1AnfhWee}??-<L!_f2{e5<L3iGTGe{&gD)Vn&E?ur',
    '}hC09S#!aq0=k1!OAM4H$dr65h+fB<Rs$&I*=8V78Nbe=SIo=1YJW_8|l9!gwv9OFCzda~edef<P#jkgEm!fjJN)NZ|hh<mX>B`orgk-*#Yj',
    'C9qd4z?KkBIHv+Pukg8<wLs|>LOF>d36v^562fpAkR%LLrJcucb76m7P~C`m|8(Yuyfx4ovpiGEbV4Ga*A-XO0TKI2&nt01>(e-90XibODp6',
    '>Nm6wg*sclHPO2I_9Z_i@72B_cOe^Kr2@Yxq*G53e$WYLjm5P`hX#0L=y?Gy?J2Fhpvc2=edz(YYQe^<FjFQx&jNAJ75&x4XiQ+xjGKY<uNm',
    '#5^xgU>ePO*oOa67E1GKK$RoOBrMf{%Y3!z)ir@)MxnC1dlnpU%w2zYMg=~4d~;1K9K6prvWMa6JRi%wLm(X4p4xIMe2Wd@S&-u#e<JYZD5s',
    '1-;Z_<4)zG&=6nFlw*_zNhe_KAxMTXvuNwR%@IqVg3Q<jmy&kSr1Yi~x^aQWaT{+<Q95Uq9k}6Hhsli(s-Dv|*9hYf_=;2!2*BG*Y;k`jCxl',
    '(q0#<z@Rl|_Qp&!a?G9VoT%7JT!z@))?iD|QN+?STk`(t_+CoDhnOyeil)=Q|{*Zv!u5IyE-}FZ@S&a0@EN#e2m3G>R2DVZZL>`x{PXCbu5c',
    '=VB4DI5@;iLFlCB8~A?ePKf)7y#w2#Hn%;De61ULH^$H(nrWUU*fwo$4t(9+p^Wa=mQNR|HW+oNEo@=>hmo(Wj;3?dsR39eZk^V9!+GcNBE<',
    ')352}h*p%u82Kt-E*4i9~{(bUrwEKR+hJd4F{cghF4^7#q)T`+pN227c1=r!E-g$vI%h9LP}G8-m{Xv#r~1GLVg-p=BQokHGxEYr;)fY>B!s',
    '0Igpt5Lz54hsH@@&+V5F7xPu2Y^Wx5nVwh4zLKZXk6i@h!E$jgg}QBOANYlatSFt;waxFVI7(x{CXq~%pf+Wxrb(^lKoUTB@$DQ#ao<Jaz&A',
    'Bh1<aQ1X2Lp0|o`i*J@Y(4|1B!A>sqCK;<x{+02n7b&Ijzqyd#fvpZ&Yhgw$YQeg6z6)7FHQP-qMVF;@Ju$nFd&A^7kb?>;wi&Ie105p9N%l',
    'YSC{&jCG4h)BKGzE!STxd;Tm9RMk<hMsyQyyS_DhdZPw?bhd6&?TBH&Cg<zJ|uV0zVP=VWjuw;Q6=M9|rbk!IasOq&6Vu7n1zFO!3~Xwq7C_',
    '#Q6X9{iOAk4Q=KO1en!6MSsC6r@%8=3h6C?c(Z5KL|pJ`K4-atxG2x<z7+RTPokDHpFwW^Dk_y=LOv2zRly?#%lQ^=dtM}<X<Ni3*EsVhgWA',
    'X)!so@jl(Ct}Z8{m_{np!?hDM#li8SRl7HW{ZiH5G)cLfH2j%E8LL8M(@$X%^JlyXQWZn{R##49|fgV~Wc_;yerSsTe1K8H37PdBu?JJHVGh',
    '<(@A3h(0$_UW0ye>SzQvb57<Gb)lRX>a!TE0OE7$*5RR!?MrQH~_(Dlo^^9hBG#^0@Jp%z;xWuu^lV0Y%iQrJum{>aad@Df$zG8VS0hCn-*i',
    'H<~q)(p$Co!=owCcw46{6XWC2)LO-w!cV?S2$DD@D4NTu*L4bLs>6vaY)m-1V9778&)3iMgw6iS+3_sjd3OJS2RwOVx2mkCGkL{!%Ub1w_%6',
    'yI6K_V#C_>LJopfE(g7e@z&osP%Zg5^x^>p;>Crrh>9K74gs7hOo)Z95#j-hbKYagye%LK<Vn?Nful(9v|q;*^g4Q=IM{z9x@}(UN<2H$A<c',
    'u6qx9FL%H1P<y@xF$XM{h2V<qG?*IBZj2=>NfBc>q}52(v$@~(x<FF76UDKY;<4(yYJvG9L!TxJGYL;J$@WQa`+ow?&5u_B=CDyhmQg?<NUW',
    'I<wV<!I-yC#!IfB*_^DaN@)zCw<{Bw+f{F%{<;{`?EB~J$5aAfK?Q<v!_J4uyCoZusnjL0`P+M)4aJF%Sj-}KgoK+mk!^$uEhk`lb#%o;y>I',
    't1lZT5$+T9-kcTZhyNeibj}yT7OEjlTPG2`@-las(MH83mcUU`~+hQPdh<9!P6|$Rf79KhSuzSi0x}$y2(8Y8s>!TVX_h7*_cwDf?#-2Q<#w',
    'Hgbdd=Aj5or02Gi%HcpkE@T2mvd@9ESr2DXq^%=l47e}zl`A-Cv6wEj(*ZkS#6O!QROO_0tSMKDzKE}_}qF})zaYWc`jgi0Mfj3P!NEHhRs!',
    '7f_<!~cx`U0mHM|``Dm)_K;mETaGiNYKo9B@uakrFR07u7LmK?*$efLXMs<^mfFvSh5RPk<2*t5Zs;^7sBLsgJw$G+4OOF_o8jy2_d`tyg1{',
    'W@{X)TivpxC5*nE=XCw`M|`ST*<-*TEg~Oml;shPpVWF&m;8|HXE6BbS)U$n4PTTJB-qZO*LzH!K5KUoo6eo-Z1A9btR;iACxn|lM0gAb!gJ',
    'SVm`R%!1S~5T@A9Z*TS8|b42&69fqJsrm1^!(?<f2?zyA6nT|tLqctft+d;=w?W-Bm7F1OaKq&C&LI()9rtUAJ4&^X<gu+n<UNh40lW{h!Xe',
    'Q|RG>2#O1;J9Dhq8w5I-YMjUco;5ZT212&H=IxFiJU%aq1x)5xMG?2Y5RGKnVH1yS+f*PqldzZ1r>;>tDP3BZhA&&K~9C9Od16e&u6D+<G$X',
    'A+1?~c;VC6qcIGMVNeMD-CD>0uk&C9+f*-vq;&;E0qF$1!<+xXCl(S7PAv}|q>m6ph_U3XUnfhf6=z>P0^-hKrY&{`LP<9Os5b!Ap%3eWamZ',
    '$Ta6-86#79~mvYY9FUA^?5dYaSw|R!y_?O3}%qh6KiMrep!g^p7i?UDBYCs2}A>Dt&7^p+2jHPh+MQtUQJvG*>tVJ|qgBwE>Lls$t<Hj@@Bk',
    'Ou!3F#~bTf+(;3(GJt?4C^mF933N20kr`^U?n)xc*=@`_60f4KE)6A_B>>hEjSzum%%4>FskYvmzp5V}@>SWWz~e<ihFxoEJrKnCSb+mMYR=',
    'j~AJ6J904)I^S0&*!QV@AXmr;P#HVm>;UqX0j9OjJGCH@lUOHgYLAGnYcE|CdtXw`D`7f~DlXoDpyye*zgCF`-8UM0mIcLGfj&94~rY-Ig`G',
    'n+a#Wxmd+;aQ#rIk;^aI<>r6;JDQEeRt|u%nql_utV4NsOMRB;LVJg>r;Ir>u2uNb#&J>!l}n*p`lHK(9|glroK-#m+8LkYRsUaW`?fKEPFN',
    '!HL3+O$Fp=x>ty{j`o%8*-g5B`+Tbm|*ZXe|-X5PHZXX?e&l{M-7yowmclW-R2NlrUC;40PChg@JT5l^4dcR6Dl3w!NSU+82{3lhOZ>n>aHx',
    '=sT0yMbnRH`fEeyw`0Lby2xV8#OY5R1CRE-hn;x}XI%h=QTpENwGHaM7$&Yt9iDVxAyfDp>y~%GcE&R?7?^kt5?*Uy)Ev6Lj`TQ0?pD_ji<^',
    'WH*(BAy^@U=yR-!nnfSeQ5X^<M7iP+UR|<Sg}`WzStvh+8CPg2?L}{1GWs3Mxw*ptnAcVVKIae<PJj;_YIrqTV(l5<7rtz*u}n8^BJ~Tod*#',
    '|e8qAq=ji6bf!RsCOTGYGN^nRw(SpvZaE5&uUA^B~JZ$NrIdU?Gp^}=p$t=}L$OjD21<3{{G9ZZGcWxS*{6Ua=<x;_Mg*Ed95`r!2;DtX={s',
    'k|aPisLFx4VVu}N<h3dc?mA#uSM<Pt3r{>;*nHyyNF6J{UEA9pa-uJ*?tXc%Yw+~VNS22cF0<!!r2VGu(-o=vd-AoCt|fv-;bpAem^>URt5H',
    'FH{GYIZzbZvSfR$cTnWEv@*$qXmEy9|vHJSOn_Ye@s5K^jA?feKHxJt+kzYW3gZlx`h}Njxk1Mufl^S$DEFfU0Ui8kN_)-3=_OtYs+wwCAK*',
    'pQ*AevMrgNW+*M;>2FI(Yn}B3EqIt-dDaAT3etkIRUg5s-B7`g2q&u`eR_GQ{2p&3z1%Q0;`43CV-<RJT9Hy-&4!CngpgN;f9dV&%2)By$U`',
    'c|p6F(RfG%$Z;62`BuyoUCU!3{8iZ!Sle4rBOH=0Gv!gA@Z(y1P0C4CFqwdZtY+|AJJmB)#q4B0t2%t^mgQ+LzHUq(a0i2Z7Kq5SVhXbATO`',
    'BrgL;M1&{fwUA5o<}#D&yOO8NwE{3gLusYwlA(ty=%gZlCk%4K@XbbsXwR^9s#+zGba-}?%L?%reryR=v%q!la%gyy$C%Hj#83TZNjuq4d@6',
    '<Jb3B1131V^QLRAA|%a^6R?=h;nLg!5UBgtj(4+)p13Y7YMcT@7(BliZ`>ygFLn%gF9)b;wZp9JL?p0BbKyl{l$3XyMnBt80)?v)_=>rZ)A*',
    '?>6#&PXC}4uFmxC^y4K9GOi1Q@23en`S+3*Lz&14Bb~Hvk=7ze*Y&Q&bBj{(0rXGZ$tvNO`LJx9Kjd{#)eZ#gj>Nx@AkB;dCCbg}pX-u_{dH',
    '$4z-i-Qm3Uuw!_4WS&619#v',
)

# Changes made since the previous Clash Effect release; also embedded, no ZIP needed.
EMBER_ZAREK_UPDATE = (
    'c-rk;i*nmWvi+4YcWallDHs4jkdz{)D2cXpqgP3?Q;Fqb2Ec$s1Oiw*BrCG2?nm4&xSw{v<aW>CF#sW1$-0u**;Fb5fqC|HpFY#mliN-b+s_wt#rS`e',
    'H0f;Kc9vOi2@mgXJH8jN&ZgGySj-J$c<elXPQIT_PmYh~yT?c8)7|s=?!olz_57_qKRSM^n&kif`+vxlmw1-XNEC-ZGduO*kp>Q70bAV=+o#Erc&muo',
    'Y0@XqE@57}WHCuRhg}5F!{O{;Hk+TE9{<;D_k90gHa|N#-9I{?ztu!1ywL1$XLdT@n;uSI&E}`mz5O?5^P}16OB{->>ZYb)!A`$J-IT>*=%UX4tE2t%',
    'eVD?lH`CL-`H$1n*>`epc{d~8&6hRXyMD1~1H+J(jlk%<E1ELGRu+q2Q5?c1xg{%>EH}yd>(kjxIfUme;>O{sc=HzK6UKur5?%)^-gh=hkYW9;i+~Vp',
    'GhD<hNy^v6$zqy%VNksZT{mHA@tfSedr!8>yZ5|>+L(5iG+r<qQ?s*{L8hrMeWoAU+xJ78Lb;dTVhJihK0+bihtK#23dlo9vH(A@>%5yiFUGYD1L_}O',
    '^{)EC<^S}Frc8QUHO=~KN*A>9JkA(Ny%lqa#psG$(>U;gMZ)!b_v8&(WHfe&7erY~x<Qx{mtNK^#SVQR>?aJ8p0YOR{YBv6d=nhEO_LO*ny=;-Nm%Sr',
    'X`peK1=6&9D*y7FKSD(+a~ux!nmH1ZF1<vN^radT;o|GsF!7Xxu*OnZv5r0QCb0ozl$fo;E7lDaT*zMDLbHb4I{${N7AI@3lQi}&*&&TD*T1<R6x(Ms',
    '?yjl-A3mG9x_ti0Rtq`Nhpo7pE@MVh(A0DB01e)jcARTFeC_tg_6yO2^j>j2A7t6>M*Q=WNCBskQU5sbZ+gm#M#Y!zElE)TVDgb7p86yT6Z{E(`s9lF',
    '_zZvgT<0UjbI4t<*B4_EGp>(Al0sezEc=yrg>z!uieW-N$s#*kfpL?F#T!d6<#wN>bQLASw13WEfhqX4V8IQ0WrZYVK3l{zS_<nHps_>;>8&`F5ify3',
    'd0=xiOP68nrSSR+fGP+Hbn-l+aePC<EQR)1LTJnYLaf-cLFP{0ChzLChr;jDG^O^XgcH>~g%aEY++Wl3c@=DS-4;RAjYZTUq?m+<<vfL>DcRoM7InnW',
    'fBXZ!Ag~firtr3C1Nv43PAe(;gC|hk6^~H$N%_%B_P`Bwd%d!A6q1*Vs6hInct6K-(X|kaR~O7zuCW#TXd~5Vb0kUNbT2xbZC-Tx#DWgUw?tJYL$V2f',
    '#={zvQpcI6G0j%ATb3N?yre#;m4q3crD4=n6?Hu9<9EII?zu$NhNX=ZnqKw_li@=9j<JaBgw{V30zz7N;3kO$<4cJ{S9Bpra!egBOE`^Qf#4ZX1(1Nv',
    'qC(O~$LFv@4s)}FDMjmiWZ3l%w%3i6WEqBBQTRCe+?uZOH+UV8E*crv!uuT8A0R!D(2t-Smjrwac&tNEmLSbmoFKxC7c9tN!JASc-N>gm;9dp4Ds)r~',
    '3)q*#+uX&8bU|n=a6q5F@b#*cU)P7@HsyCeM6i57?{M*4#a@DycYC-_-HNW|Y`d%W`HI4SOY|V*r&rVS*E865y&^9UriZgL^6c-oRv2W--A{dT(fOO}',
    'GJ~qvzACs~Lw8&tgBJCDQNmPfMSP0Dim&@Qa+iX~MG@Hgqz<(oKf+83oD{#3YXGV<&U$%iL4bPzc4-y|TSb$CX#vi~DM9#Mg%0yMl%9mJTnady@59)4',
    'PQrwHfEF3`dX3i75S5EJ7e-MSfUa^xuYQ(eZMU#L`x4cCq7r3bK$Rx~N-u=n7rTtYBUL`|84=6t6>kIfA>DVLJp(88NL6SjvTdW2Jay%HpL7d<$-TBK',
    'oV6G>f0IA**OhnYPttmSl?o|C$VhEKNKHeN2#FM`2p?~*Shi~p@ZCu7lSwrcsa_0{5UL#mv>}<}Q-M7M45r)5+i?a|!&17!y}@8u)78&rDqt)x_m8Fr',
    'q=<B_n~FQMTx?%c)M2Clb!&k_P5I+?9|+7QnR5DqbeSlMLi;4WiGU1&Bsnj|>dtDhNpwR6BjJOP#>wLYn`8tNxC}!35*|_VS%A(I-!2)wx&f1lGuB^2',
    'malT<raNcH2XD@2WcT=R=grwywS1Bt4hH6$9SZa*2r+OASjoU<p<7Yo+p2TUTBdn~l`be2C*M);7Zw1Ai9_V&K>qC|e1U0a0qp81{3|vG*Ng&Ah}w-d',
    'F<!xW6mJHwZ^NPqa|owZWEWe4J&asQ9=37`I}JqEi_XHQurs*mG=@z`S(bNSa=&NWMBA#DT-U3r?x)pj($ub8$9NQ*{Qb6l9CyI){ujO;(sZf72C56T',
    'qrvKzzlZ&MX3!%~iK6$EG<@lOU`|)--F+ZC)3g0ua(1%!)7n5lm#N7>orO;x_wJv)j~Wo<w%U{dw+fTmyrp_0ck++=s85+4dVW_fFO_cF7^p3w-!EEm',
    'TQ?5HJnDk{T(XlfU@~mM0I3}dW_($8QGNjGz+lBKA0UT07oE-4p803d^GF^iF4dEm1`Eam8dO2Z%Pp2~YS3UM&EqrJ$>JpC&SmK_PE`uWppR(Yi7xlj',
    '?wRhXteJfRM&)>M;dX#OE`TaNY~BNI-uLwC7J^^vbTZCavhZRWr^ENOl7mj!MmfF*hGhuUf!=lwj(5Mq`p~gGaR$tM#CkkrMWqr74jFST1n&hCXpUdn',
    'rNbPJwfRYV^V-L{&gH7cgE}=ud;F;7&q^5VV(jMx+VcP)dktXVBZHaI8(!>X==<Sy7A2)k@*sj*x6IGvBU(`HH<+S4AAlqbfePG`4t;p(L_ixN8;?{Z',
    '7{BAT#*zxjlv-;u+y?=;@xvyJM?^H?^^orHP+J}$?Gude$>&U>VW~MmgsLI}Bw<6;jto`7iw=HtT2^|i1&5j)d`n79B%4G+sr7>35XU^Kv}P`ivTaJV',
    '77e;rXCA^gI$_k!nWlEX+TDk6&e+YX4*(R#_tq~s`2C$5T=BIvmT*Uy4;uIv#`HD?`<p#<4HO+$vELE%<@IeF7$=@j@^O{kp>+zy>We8<-ebKmsAjvF',
    '{DEGj&6?G*2q!<}Z|*+ncsO^ASnNXcfUV;6T|znlQ(v4*6Y3`+SpYsJd91nM=}KKr{|4msejV_9g<ezQvxYWm<FoA$^(cjePm2W)7*2-r@E_aaVQ5LM',
    'fnqbz2H5y_oqoCF=lgrL+`${<4(GPj%Bgd8Yy>|(FQ=xAO-i3L{FV4yRW{UG#OE>G*c!Ncu@@D`HER?7q|>U}&=j)~Dr#d`e-Y*Qw03;__$VOi^?nPD',
    '`Fd4KhM#d0eo*qR0u(cJd_3!Zu}w5p%`K6FL^1ba2S2}zS@6qE*A)Z1t7kshA}mmzQ1^)?J@fp98bp@xjK0cFGhqKh%{H!*4e?Z*^pWGEgC7)fMuEg9',
    'mw2i!CP1Vp1L27{3Gq^8EuqN8graw#sMh;lKHUf7Z*E)24aW%#r#y6(Lo9v%MMP6V+|2M@%fA`+U5m?=5jpqQhvM8{7lV5s=yqSY&3!P=c2}<T+u0AN',
    'b6|DHdk1gM&gZ++(^E{deLLEOEg(OysSdVx(U*ge&#v*@xsZ5~4X9K{)?#s$1g6(@@xV-8;l#5q3wq+>S@O4liZ?#1eV*H*F9eUqaa(TrVspsZWy#}*',
    '`Y4}d1GYbtQ8jszoT+nLO<&CRNkgA&Cv5KhVdT%FpMM7J{4Kiq8DWfPx>`PU*hU&|@P`t@gl-ocI|S#7{Je%Dp8&2_;_OPPB44Xz-M#O3k|ouL<~;Nr',
    'Ffe`OxDz%RxtcpsC#vJx&QKpuOk*-K1}+;rhCO1A<GM^WEMx2p)Uj<3N4n|`4a2moPT3x)HncZT9nG-}i!nwAY{ZyhYNkV}HW^ZtIumnf>6Shjs+3xW',
    'szaOB$fep~FmN4pWN6@Dt2+|Zd)y6)+0pFq2RWl(+!~nf*K_)RMdJUf)8jWsd-K=RAMwUQt)WNUaHz_QI}N|@_#}oRAHA~=Q5dHpfykv`Gezd*t+3fL',
    'yRzHE^zR~Xk_I<hEw;KPQYRbl>RI31obmu+OQR1ZjEjW#r%%aL&iNw=V2_jeKv^5<g=pv$HsCfdhCty3S(qgv^G_j9pJRh%8emHjV9~qO_W`ygu9fgW',
    'sEB$-G(`l&s|6kl9AGFwMa#@Xo+$$33$v71H{=!G^5MNpYV&2T#7^zP0gWQyh=emVKCfIv7<z_R7F)o^hb(w*Iv%bG85IjrX3WZ7xb@P(Urb3V+cmY;',
    'w0FCR%iNsv6(rkaL#tgssY=W~P#^`&d8o`OYzO(7<u-9C>|^sg7~E&Z87fovzLf1g@flY=A(PS}iEM3X@Z@xMHakCiC+G?NfLy1fD!gvLD5Ll+Sfop`',
    'L9|}){e8E6euv3d#R?tWU51{`lKd*lA&tHf^To8)5b6gn_^IrlLuyjuvZlA^T~Tl9#pe{e!ZeZkW`u%Gz~@~@9LzXf*g*560AtwLe(-olt-+jDg)Sa0',
    '0mFfvT%S0poDM4!o@*~~1l@V!^3Y0gFNJ#X9vIbH1K|A5K&k;IqXEkc6Gr?Hpk+ZL0G266{);#)kI_<OiYW^HIlDss=q3D=D&dXr-0=4Nrq3iH%#r8U',
    'u`o%#Omi=;ZWY_^aJBMMo__$dLUa<_^>hitw`qU_wlRL>OGGk{zhb&^k)#OhwXsY2Iu=OIBsA6(x)eql-<;G>0C03sj5Ik9nK2gdEm#yQp3~bZ@Skl}',
    'X8^4Q<wQ+xhq&tDs@o&q<VLIfoUJ0Bk*W;^eGh|IBF|Hl!0+Ev6f7yNy4n{yo`?{hhu9@J_#Sy)m4jDc^0}qst_ynUfyIN`4W-avJ_n%z5}Mt$DEWV+',
    '_6VsJ{{57CpvT3%N=_#@ktmMF`B^(Z3&|~8;n!D0M3Jm8V6miEjCb@DTz}vthygJ)i$)JNATBF!;eD1QVm2oCPWMIZ%Ui87u<skR3_y>dywL)j2g(N<',
    'JOoVfHZ%tnWLpAPVwQwH9z<axQ$WJl@d6rSG%dkXEPe`JFrLCyH4#PTJ-M$dyp`Bf2jO**F`c_P1zwd&O49B-=Z)oU#G<%F1mzvAs8nQE7q#<r>qcrN',
    'OQ}?ZUzXayk=0ZX3w^UqRE&D#^9!CY*{jr9x|nh3#W9Q=Q5%H{Yb?m}2I3G5%C|G0-%Q#fP8j?%&6R_~nge(VXu~6cYg`PaK3IO+WILbP=Sj>im{8tk',
    'EjzpMPD;@(0-@hF>lFq@Hu+#baTYC~4RGTFrS9e}^7LMjT^9z*4H{w2WIze;E3`Jh%4uxpb5)Ye>f+dXpl$Jr`ra?B+pHEdU+f09r3hSEu~C>V8Rh;w',
    'ucSC(+ATY7mgZLqFvq_t55hSE#bAz*OI5c|HhAN`5{hbSDLVd!Yyd8yYKq@4h^8q9{w}(Dff*S?083X9H-cI;xAON5=Bg}d(k<)*u({Vr8F~#y4rb<f',
    'uIqtnryfI8OF$g}zXX=}9$?H3Fy0LB?*V6lP3p=+=FD}!)?B{H5;TVTVCT+FL35yjxXQPpuoEp!j5v4>1=zoyFJvzf<O`IE6b@V<F;yAxGk!xQo9o{|',
    'R`_wG%KF(-&J?%KRGua<88;7!nu1JNDhV=IX34RM!8VWL+M5EUg=ICyz4orEyU>k1h5MIzQ5#)PhPvVS9);n=4xk_7-Dk@F-oZ?`V)-pk8)>O8ZkeGh',
    'b1x11Ea~N5hS06buU?0~!{61K_*cfV{Dyg+(@_*#;{h90y0)tzM+Cg0MMk}F-_-|kyoF5mq9eWLv_szT)mjs}(IEciSG+3EwLs-yCLPRHy$S~0>>#HY',
    'QnL>+wzV*=p*gN=sw0!>u0?fAWfs%Nwr-j#wMLFQa7M<+F{n8l82UhUnPm@{YfY$42V++=n_=3K<7$Hm9gXO~G+ijB8}K|bwb6vxhBi<grmD8-j!a{u',
    's*?e=-N|@hO)T4@rZpVb!nCkuNbU>N4(b`l$+ef-OVWiZB@E@6H+bh!O1#0N%(L^^>0AUn52oj{v-9$Qy|O97EMCH4B14yp+ox6Jd+tq%D@u(5_zaIk',
    '^34rauMTzy?cS0A=7PCTQwyk52I`N=Ex_N<_uvK0m;8!mL60sv(s8205*w@T0%qdgiUeT2)=e!I#PcWf*prpv9aPX07&EzEdMVpL?jY#njDm#9Y4O^;',
    'uEht+r|9M2DQ=1?wXxXFCeMW{E|yrCINL$8fxr3Pwz*eLgWyIF0dNQ^Ee6Q5rc9|(Owqc+NSLaORerX>=GTqZ;7xw+z~;%?w*<D5cWbA6U#LF(XYqgQ',
    ';;$i_NmbW1hRoLK#4%NUU>X`g&Uk3+6V1^rT{AS>o($}vt^x9yOl7KO;16wNP1vA`Y|z|bFmeF@sB4V%2>{$!SD85)4o!2cs&wFvsA-tGrjAGM(9~Sj',
    'poXDMj3Lz+wL5or{|_n`n_d',
)

FILES = ("src/game/game.ts", "src/game/fx.ts", "src/game/ai.ts", "src/game/kits.ts")
EARLIER_FILES = ("src/game/game.ts", "src/game/fx.ts", "src/game/ai.ts")
STAGE1_MARKERS = {
    "src/game/game.ts": "WEAPON_CONTACT_CLASH_V2_NOV06",
    "src/game/fx.ts": "clashBurst(pos: THREE.Vector3",
    "src/game/ai.ts": "ENEMY_PROJECTILE_CLASH_AI_V1_NOV06",
}
STAGE2_MARKERS = {
    "src/game/game.ts": "EMBER_IGNITION_GUARD_ZAREK_PROJECTILE_V1_NOV07",
    "src/game/ai.ts": "EMBER_IGNITION_GUARD_AI_V1_NOV07",
    "src/game/kits.ts": 'name: "Absolute Combustion"',
}



def patch_data():
    packed = "".join(PATCH_DATA).encode("ascii")
    return json.loads(zlib.decompress(base64.b85decode(packed)).decode("utf-8"))


def new_patch_data():
    packed = "".join(EMBER_ZAREK_UPDATE).encode("ascii")
    return json.loads(zlib.decompress(base64.b85decode(packed)).decode("utf-8"))


def is_project(folder):
    return folder.is_dir() and all((folder / file).is_file() for file in FILES)


def choose_folder(explicit=None):
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not is_project(root):
            raise RuntimeError("Not a supported project root: " + str(root)
                               + "\nChoose the folder containing src/game/game.ts")
        return root
    for folder in (Path.cwd(), Path(__file__).resolve().parent):
        if is_project(folder):
            return folder.resolve()
    try:
        import tkinter as tk
        from tkinter import filedialog
        window = tk.Tk()
        window.withdraw()
        selected = filedialog.askdirectory(title="Select Fight Royale game folder (containing src)")
        window.destroy()
        if selected:
            root = Path(selected).resolve()
            if not is_project(root):
                raise RuntimeError("That folder must contain src/game/game.ts, fx.ts, ai.ts and kits.ts.")
            return root
    except ImportError:
        pass
    except RuntimeError:
        raise
    except Exception:
        pass
    try:
        entered = input("Path to your Fight Royale game folder (or blank to cancel): ").strip().strip('"')
    except (EOFError, OSError):
        entered = ""
    if not entered:
        raise RuntimeError("No game folder selected.")
    root = Path(entered).expanduser().resolve()
    if not is_project(root):
        raise RuntimeError("Not a game folder: " + str(root))
    return root


def normalize_newlines(src):
    return src.replace("\r\n", "\n").replace("\r", "\n")


def matching_positions(text, sequence):
    matches = []
    start = 0
    while True:
        i = text.find(sequence, start)
        if i < 0:
            return matches
        matches.append(i)
        start = i + 1


def apply_hunks(text, instructions, filename):
    modified = 0
    skipped = 0
    offset = 0
    for num, change in enumerate(instructions["hunks"], 1):
        before, after = change["before"], change["after"]
        target_line = change["line"] - 1 + offset
        # An insertion leaves its original context intact, so check the
        # *updated* context first. This makes re-running the installer safe.
        if matching_positions(text, after):
            skipped += 1
            continue
        originals = matching_positions(text, before)
        if not originals:
            raise RuntimeError(
                "Could not safely apply change %d to %s.\n"
                "The code may have changed since your upload. Nothing has been written."
                % (num, filename))
        # Pick the occurrence nearest its source location to avoid altering unrelated code.
        loc = min(originals, key=lambda p: abs(text.count("\n", 0, p) - target_line))
        old_line = text.count("\n", 0, loc)
        if len(originals) > 1 and abs(old_line - target_line) > 40:
            raise RuntimeError("Ambiguous code location for %s change %d. No files changed."
                               % (filename, num))
        text = text[:loc] + after + text[loc+len(before):]
        offset += after.count("\n") - before.count("\n")
        modified += 1
    return text, modified, skipped


def atomic_write(path, content):
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".clash_", delete=False) as temp:
            tmp_name = temp.name
            temp.write(content)
        os.replace(tmp_name, path)
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.unlink(tmp_name)



# Final rules: only a successful melee destruction of a hostile NON-BOMB projectile
# earns a Zarek Clash Momentum stack. Blocks, parries, weapon clashes and bomb
# impacts keep their normal mechanics without granting passive stacks.
DESTROY_ONLY_MARKER = "ZAREK_PROJECTILE_DESTROY_ONLY_V2_NOV07"


def patch_projectile_only_zarek(code):
    if DESTROY_ONLY_MARKER in code:
        return code
    if STAGE2_MARKERS["src/game/game.ts"] not in code:
        raise RuntimeError("Expected Ember/Zarek projectile update is missing from game.ts.")
    changes = [
        ('    // Zarek earns Momentum from a genuine melee intercept (player or CPU).\n    this.awardZarekClash(defender);', "    // Only an actually destroyed projectile builds Zarek's passive (player or AI).\n    // Bob's bombs explode on contact, so intercepting them does not grant Momentum.\n    if (!bomb) this.awardZarekClash(defender);"),
        ("          // A clash against Kaizen's rotating chain counts as a real weapon clash\n          // for Zarek's round-based Clash Counter.\n          this.awardZarekClash(attacker);\n          attacker.clashRecoil();", '          // Weapon-on-weapon clashes never award projectile-destruction Momentum.\n          attacker.clashRecoil();'),
        ('      case "blocked": {\n        // Only real projectile blocks count as defensive clashes for Zarek.\n        // Ember\'s beam and passive fire are strikes, not projectile clashes.\n        const projectileClash = ranged && a.type === "projectile" && d instanceof Fighter;\n        this.snd(projectileClash ? "clash" : "block", projectileClash ? 0.88 : 0.7);\n        if (projectileClash) {\n          this.awardZarekClash(d);\n          this.fxp("clashBurst", shieldPos, "#a9eaff", 1.10);\n          this.fxp("sparks", shieldPos, "#d8faff", 34, 8);\n          this.fxp("ring", shieldPos, "#a9eaff", 1.4, 0.21, 0.8);\n        } else if (!ranged && a.type === "melee") this.fxp("clashBurst", shieldPos, "#ffd27a", 0.72);\n        this.fxp("sparks", shieldPos, "#ffd27a", 16, 5, dir.clone().negate().add(new THREE.Vector3(0, 0.3, 0)));\n        this.fxp("flash", shieldPos, projectileClash ? "#c5f4ff" : "#ffd980", 0.35, 0.1, 0.6);\n        this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.4, 0)),\n          projectileClash ? "CLASH!" : "BLOCK", projectileClash ? "#a9eaff" : "#c9d3e6", projectileClash ? 1.1 : 0.7);\n        if (!ranged && attacker instanceof Fighter) attacker.model.recoil = 0.6;\n        this.add_trauma(0.14);\n        this.hitStop(projectileClash ? 0.085 : 0.04);\n        break;\n      }\n', '      case "blocked":\n        this.snd("block", 0.7);\n        if (!ranged && a.type === "melee") this.fxp("clashBurst", shieldPos, "#ffd27a", 0.72);\n        this.fxp("sparks", shieldPos, "#ffd27a", 16, 5, dir.clone().negate().add(new THREE.Vector3(0, 0.3, 0)));\n        this.fxp("flash", shieldPos, "#ffd980", 0.35, 0.1, 0.6);\n        this.fxp("num", shieldPos.clone().add(new THREE.Vector3(0, 0.4, 0)), "BLOCK", "#c9d3e6", 0.7);\n        if (!ranged && attacker instanceof Fighter) attacker.model.recoil = 0.6;\n        this.add_trauma(0.14);\n        this.hitStop(0.04);\n        break;\n'),
        ('        // A perfectly timed projectile deflection also gives Zarek Momentum.\n        if (ranged && a.type === "projectile" && d instanceof Fighter)\n          this.awardZarekClash(d);\n', ''),
        ('        if ((!ranged && a.type === "melee") || (ranged && a.type === "projectile"))\n          this.fxp("clashBurst", shieldPos, "#aee9ff", 1.15);', '        if (!ranged && a.type === "melee")\n          this.fxp("clashBurst", shieldPos, "#aee9ff", 1.15);'),
        ('    // True blade-to-blade contact rewards Zarek once per weapon clash.\n    for (const f of [a, b]) this.awardZarekClash(f);\n', ''),
    ]
    for i, (before, after) in enumerate(changes, 1):
        if code.count(before) != 1:
            raise RuntimeError(
                "Cannot safely update Zarek rule %s; your game.ts version differs. "
                "No files have been changed." % i)
        code = code.replace(before, after, 1)
    # One call in the non-bomb projectile interception path, one declaration.
    if code.count("this.awardZarekClash(") != 1:
        raise RuntimeError("Unexpected extra Clash Momentum reward site. No files changed.")
    return "// " + DESTROY_ONLY_MARKER + "\n" + code

def install(root):
    earlier = patch_data()
    newer = new_patch_data()
    originals = {}
    outputs = {}
    for name in FILES:
        p = root / name
        raw = p.read_bytes()
        originals[name] = raw
        try:
            code = normalize_newlines(raw.decode("utf-8"))
        except UnicodeDecodeError:
            raise RuntimeError("Cannot decode UTF-8: " + name)
        before = code
        # Supports EITHER the previous installer OR the original uploaded game.
        # If that feature's version marker is present, its hunks are already live,
        # so don't mistake newer edits to the same surrounding code for a conflict.
        if name in EARLIER_FILES and STAGE1_MARKERS[name] not in code:
            code, _, _ = apply_hunks(code, earlier[name], name)
        if name in newer and STAGE2_MARKERS[name] not in code:
            code, _, _ = apply_hunks(code, newer[name], name)
        if name == "src/game/game.ts":
            code = patch_projectile_only_zarek(code)
        if code != before:
            newline = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") / 2 else "\n"
            outputs[name] = code.replace("\n", newline).encode("utf-8")
        print("%s: %s" % (name, "will update" if name in outputs else "already up to date"))

    # Every file is checked before writing ANYTHING; conflicts are safe failures.
    if not outputs:
        print("\nAlready installed. No changes needed.")
        return None
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backups = root / ".clash_backups" / stamp
    for name in outputs:
        backup = backups / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(originals[name])
    try:
        for name, content in outputs.items():
            atomic_write(root / name, content)
    except Exception:
        for name in outputs:
            atomic_write(root / name, originals[name])
        raise
    print("\nUpdate installed: %d source files changed." % len(outputs))
    print("Backups: " + str(backups))
    return backups


def report(message, is_error=False, use_dialog=False):
    print(message)
    if use_dialog:
        try:
            import tkinter as tk
            from tkinter import messagebox
            w = tk.Tk(); w.withdraw()
            if is_error:
                messagebox.showerror("Fight Royale Update Installer", message)
            else:
                messagebox.showinfo("Fight Royale Update Installer", message)
            w.destroy()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Zarek gains Momentum only by destroying projectiles with melee")
    parser.add_argument("project", nargs="?", help="Path to game root (folder containing src)")
    args = parser.parse_args()
    try:
        root = choose_folder(args.project)
        print("Game folder: " + str(root) + "\n")
        backups = install(root)
        report("Zarek projectile-destruction-only update installed!\nBackups: %s" % backups if backups
               else "Zarek projectile-destruction-only update is already installed.", use_dialog=args.project is None)
    except Exception as err:
        report("Installer stopped safely: " + str(err), is_error=True, use_dialog=args.project is None)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())

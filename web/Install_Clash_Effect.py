#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fight Royale Clash Effect Installer

Standalone updater: patch src/game/game.ts, src/game/fx.ts, and src/game/ai.ts.
No third-party packages, zip files, or network required.

Run from your game folder:
    python Install_Clash_Effect.py
Or supply your game path:
    python Install_Clash_Effect.py "C:\\path\\to\\your\\game"

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

FILES = ("src/game/game.ts", "src/game/fx.ts", "src/game/ai.ts")


def patch_data():
    packed = "".join(PATCH_DATA).encode("ascii")
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
                raise RuntimeError("That folder has no src/game/game.ts, fx.ts and ai.ts files.")
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


def install(root):
    instructions = patch_data()
    originals = {}
    outputs = {}
    for name in FILES:
        p = root / name
        raw = p.read_bytes()
        originals[name] = raw
        try:
            code = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise RuntimeError("Cannot decode UTF-8: " + name)
        normalized = normalize_newlines(code)
        updated, applied, skipped = apply_hunks(normalized, instructions[name], name)
        if applied:
            nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") / 2 else "\n"
            outputs[name] = updated.replace("\n", nl).encode("utf-8")
        print("%s: %s (%d changes, %d already present)" %
              (name, "will update" if applied else "already updated", applied, skipped))

    if not outputs:
        print("\nAlready installed! No files were changed.")
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
    print("\nInstalled! Changed %d files." % len(outputs))
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
                messagebox.showerror("Fight Royale Clash Installer", message)
            else:
                messagebox.showinfo("Fight Royale Clash Installer", message)
            w.destroy()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Install Fight Royale melee clash effects")
    parser.add_argument("project", nargs="?", help="Path to game root (folder containing src)")
    args = parser.parse_args()
    try:
        root = choose_folder(args.project)
        print("Game folder: " + str(root) + "\n")
        backups = install(root)
        report("Clash effects installed successfully!\nBackups: %s" % backups if backups
               else "Clash effects were already installed.", use_dialog=args.project is None)
    except Exception as err:
        report("Installer stopped safely: " + str(err), is_error=True, use_dialog=args.project is None)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())

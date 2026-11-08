#!/usr/bin/env python3
"""Fight Royale V28 — exact-anchor installer for the November 8 V27 source.

Features:
* Roxy prioritizes Frost Aegis Z over passive turtling, when safe.
* Guard Fatigue icon, counts, multiplier and decay visible for both fighters and CPU spectators.
* Zephyr Rhythm rewards actual attack contacts (including blocks/parries), maintains
  its existing 25-second refresh, and never spends on F switches or parry counter.
* Zarek two separately defended aerial melee attacks per jump.
* Aster: defense 2.5% per stack, shield raises 50% faster.
* Ember: +5% outgoing damage per active flame patch (max five).
* Marina Water Ward: 80% absorption, unchanged duration and cooldown.

Only code from your V27 project is modified. No new npm/Python packages,
new synced fields, or SQL changes. Every anchor is validated in memory before writing;
backups and rollback prevent a partial update. Run inside fight-royale/web:
  python install_fight_royale_v28_roxy_ai_and_balance.py
  python install_fight_royale_v28_roxy_ai_and_balance.py --dry-run
Then: npx tsc --noEmit -p .
"""
from __future__ import annotations
import base64, zlib, json, sys, datetime, pathlib, shutil, os, tempfile

MARK="FIGHT_ROYALE_V28_ROXY_AI_BALANCE"
# For project files, the anchor is more important than the version of the installer.
PAYLOAD=(
    'c-q|?+jiTy@mCNx*(KL9b@3|e^(8rq?`JnoYCG8`aVkS1C}B+zT7tB#I69|)(3hUmhd%W5E86GwPx=GxCv*lNDUhNh+u7}In}=8e27|fJ02s'
    'Y{x74EpR`qzVAF<Gh<Whw!xq}|5Zjm}!CQ+YDXGo>wmux?#p-a9XHK(cmuQfOB0^MkCkZP5@Zmg}7mW16%!)ZPuF7sF*85zQWjA-`)aMs^fN'
    'GW9``L|9iwO7Edqmw>ozPm?dM4sY4b(pO=^_snLmlb-}7vjPRU|+JewMEXB6rE>F8myTjwo^ukRG3J!_K0{CVHXk4y=12g9wmER1abGmXYy>'
    'xCLxRBFqo3%F_86)0l7+$^^LRO$Hq4U*MRmIu>aX-WFj8svjGcI2#<#VVQUP;-0(S#`p$p{R<n}Ze0R`c;Y%8I`%K!YA*BLkwA&}N8vz{gd{'
    'o3T+6YyI1h<y%71-V>c|vM7xzU>sgv)#<WL?31vIU!dxseikwuIo!JzLr!;}lhDsn2Q11Nyln40l_RfFN+mcNFdSJG5}xks|C!vIaH~0?RNS'
    '^=Uw;?`xp|CLVMJNTNp$UM9Ra<b?vooh1@Nc>wDe56LiOmt4e>c(L!pHxV(AhX@>v4)zDd4HQ`~X&7<pD>}AFp7XrY44c**0kZ|I=T<(L+Tc'
    'EtoU1HtYJuop?1f?gm}rFV4?=mGeRM)0B4;QhR}#1e4^+#F!z+5&qg{~lhG`CEe5A&z#RGo3qjUl!Xq%<iR;@xXuAy}{Ad*b2*bdQ0!0CO-^'
    '0WP60Z%%*QrxeAc1o_RjSL`D65!d~GR*oyShgYl3!y|`@J3TDV2y!*KpO`{grui}v@fLGAZ`ri3*y8mJdz|1x?sjVSf!99IDb;5%`ul@$S=X'
    '?h#S(L2#))ss6RMiA?OrnSkV!T(J<IC<}En^0D;{eQR@35U?4)29q~X|DmKLd{~?BK)gMXTg+<_wz;#4~M<|h3z)5u&r$zyYC>g|l#8)C3_E'
    '-eqzRx8}84$Yh&<7+D?jnVM2~q@<fRhG+h`_kQfli51`F<Jc+j{#V2XjEbVW8YC60j?B!lF$Xfq(R#SazuhlQoGX*GUj#@UEm>uM@r8UMC$P'
    'd<J3frX-g<P;mz!ff>((eDd+5Ry~(H;wrH0EK!;Ml%bf-FCx~Y6}@_%jP#0)MerynrwdGlR_dwa#gwU4eJZU)MCH8AT}@p#TW!Km*|)AksDF'
    'k28Zr;8sE<iRXO2cQ%~o9z2ayYs*2ofiqA=FvjBn>W3yZRMXG?zb3`WkD`ix$V^vACLbE*Ff;p=+`@}VEQOj_KvGtayolBva+w+?9-jx?{}N'
    'L7OIl;{{H!Q9ci<dA_lG=sO{NatGNyUzjFmZ3EKo*7V1oeI(_3@q2}M_+E-2Xo5YUdD+C{E_0#Nf;p%c;b-+g-a6g0q{vfmT-*w!~^CMC^nd'
    'L4~h*L;eUpJfV8)}FAv@vw|9<P`!9~#JFTPb-Q)J_`nuKv)^RbI5FZTTldKR7Y6C7Ma8V^4ACd@YgbtjES7q6RgLr7rWe`^Pv}&*_$ui8OLN'
    '%hwXP-^@12gLLC^4Qe{e<b!Fd*<3h|P9xVMc;Oql-f~*~M?@s8v3>I&ZQ$XA-@^HbPehH06!ij7l*&lojd+?|NvREkT4vUNd;CvLnk@K?P&}'
    '>A~^tuJam7N)fJNc~W!MzJmX4yD|~N`SHP<(}U;a;Z26e3|8an>N$$@SDmjskFDZ<HRo}?5GAMV<8|x!uyu5L0v7W1I-x4BDr<&p7&0)FtU9'
    'j1P&YXeBELz<&J5))b^?+vSP7vyZe9cjU`>V%BzB<|DkJ*%(HPOzlp8{`x}_Q&?m9q87|HK=)CYZOO4`6C9EjS+Ns2&4Rj;Xk%LOf*DBvWYt'
    '&{n-fzn#Mt3kb~xz~-=_Tl!6qm%aDZ`#MZFI$Jl5Q|pyIxJ>H2(blA0MOt-Tr#&9W5Dj(QApzfwXy@DQ~$bx_W{eGh(YfQr&fDxPY52*wCY<'
    'MwX?QbDOmKu;m*$P5xIq7PZm)S+Q?7OO&=H(ePJRqbteEG;HiJ`Z9V4?&Q}e?8>S<sCZi3KJ#B5HM_`Pn!H691w!Y13N;Ds-s?a3Tt733Hb1'
    'yK?ijJeqt*HFR@q;SrS304%V5-baQX)=eZl&2Ls#J9{gxhd9=@TxsbAo0i1FTR;f|GVes<cp!+Es9A(dv-rI;gt>Lwp~s;lCTw@oyrAq{_fj'
    'Kz~%iXm^0@i)5*mMp+^-oIvMit?L7I)VqZfZ4_2#1!smPb7`_n?(WpN<KWC7ldst;<Q$A0XdkaXym9gGdEVJSC3m2o6;j7-k_Y+wUuVspI+5'
    '7p*UYtQ_E?_h5SwD0?Rvy%uGvNfg|f<4+Vg`F!Kj3)arEK8JTi@o7g2@6Nbl)6%JlZ&Ox=swi8{uq8>tCt$%UA7hOz8hH^iqM<|8-zuUf}DW'
    'UqC4xc_PwcrvAMN&T3uqgKmy7$*ltE#d;ikbzw7Ou`L&{Et7D0q(Fa9ZfV*Pc$*%4?=|^v7M0EK6tg0#4vprk$rJRKCn<!le;`k6+|nD4@7c'
    'sI>$8Ta$#-VPg;b7|KUUxKgcQ@bbL0DRfs+p&K2tne@PO(#hphm!mC2s;^DIxj2tuW<mTxPpcAkUa6q^Kpc4qS7YwfhYLmP9=t>Z(!%)wssJ'
    'uR&E--6+9}k9Qc*^Oz>qWTiBK3G}t#9fxUQT@8Ra9oqdIS+>_qYW%_qcuf>ge!jA8*?-(8>%9%cO2^{QMNmyl&U>E?&4Bceig*;6{<CfTp#X'
    'QQ4@JgQS93Z~~qo9*Do?+=0g~kPF@g;=RL9yGKqucNcHEcTsAvb;Dp_@$L2kcT7v<gz#U-EH)tSfoYCE-eR|V8^bx^Z2J#yN)<LfR|#5y)Ui'
    'nVQ80eGhI3mKG+jpX0_lti12N7EDj7|XPa;jviPJiT1Hd=AIv3LGZ`IE4>MN`7A6A_Rt1zuQygRTnL{q-8xyUu9E5B01%B}_t&J=VMj#6Bfs'
    'mcF)?mr<|7ucIE1Tx_=!H^nYHd%~Fo1`(#R7n)Ly+ZGrw4o@&x-2k=3`W=H?)aLh#zn9n!r{x!31l(P8lAy0%*-L^4r-YpE|a_|%I~M7X_l1'
    '*oMKA3!UIRQ_<*q>l+R54jXXda?O(}hJIDdFf*#&<WP>d}XhkoELlLkbvI<v?>KNQo=Qk@6Km)@h){yCy0SQDnfEseZe8$u}(FMaRV8X89=#'
    '@R`n-7&UURizt#x~O{X4Q#MPcO>bpSXOM0n|1Y7!d5+oUlWA;mw2KY0T&*;c)g*39~FNdudQ!H$xmDUU^!-FN(b0y;2q0wrvE4{{c>(&R}HT'
    'ax=Jj^CH^<8P(?)fK|@2Nt8NYgfwu)z_P(h-eH#nJ_0nG>OrA_|9}1X{X6~2`@^^FlKJoRjA>s~=giE0xBGZOXo(7OBfI!ASWef+kNJsPNyz'
    '^B*qJT)TsYoV{#tH(NU2qGYHNzRdc6r2cV{&BmD{Y{%lS$#3PN!`I=SG!j~OM5;($jZ%Ue$`f-6KApWP^JG%))LG(t!)$1i^KroDIk;^eg5+'
    'TA}qX}1pX?uq>KcYh$R2tJPp<dO)I*%goQlDZfBG)$fwulgJ&-r^N^$f!GVk}i#H>;+VBQOP1mTr`Mymk(7>OeJ|vjrx#OdVQE9d;kY*?1Ss'
    '`DA%5WytY`6%a<V+;cQ0Bn<l(`lbvpz@IoOYtu)W*s7Si=)M(mDf!~Dr&8TI(Nmf*Aum*{Bw*v0L*avm@q2{`M%7bSJ`)p*6@E~atGcg0zU0'
    '?-U3?T84r%y@UPJmP-(mgC6o~j-vlczRCK`9<`*wmzM(*!39@!dOVOv}wBEq;Z?y10IzitEFjZ+G=FbM)D_FSfra@66Cw_kp-dYaviMqY<QH'
    'ab=lTHwdzsHa3BED}s)oxM@Xm5clX%d1Ss9s_R3UW!a8o(HpB~J1*BxC8xp?^Fi$#_F;&{7Y};6HiMnSjH8CY{O}SqucvA`H2Ti=R55;g9Cf'
    '4AdhkF^B9x^*InijCYF<@@+HO%Cn;MZ5s{X2FQg>>3uF~$wlfH<GS{a7odu)&NnM9$80kc5BPf|LDkeTT~?d$1}ND++cZY(6*Lpsutrw-RS6'
    'CBDl8v}-@0Yfh*Kg19cT{L|CNP>A|t(g)IA!SF0qHsha0Z|2fE*?VUQSpUBIHKSQ0=qp^1_<?4Od_-+;s{sy5NgerG*d0WhZf$d^H>G*oRo~'
    '&#_aB@2St0q>bZc&2p^V4`PgY{kHTI=_yZ^GgQ4n_Tw7D8^Azw)4VX6{bV$3{E<ANfRrDxqSQB_qsyVA`CZG!I2M~IU%2$njN7bv{O5KG10q'
    '?wE^xgXew4bijK%n&?g0P!}tiqWqo7K5w#-zkFN7RFH(r<}2<6^Tz7qSdwfY9XuRjo=oWU2<9%h(T~((iB|GRB-ftz1UUOGxoL1@p;ScUHxc'
    'ozL{cICc%a1dFx2ipWeZA;<uhLmq7FC)i^q;dm(-tRP8^lrFpD9y!pG{0sOe;Mqfm%JOg19{vvVM94^wff{&M*AU<a_h&%ME#}pI5Z!Ceu0V'
    'Fz`SZ!99Ma&)&CpSAS>w&B`o7u0A@wQ+L!BojYlv!0*t)qP5R!&I9pQB)4}f5{;`!`aJ>&Yk7aT@xAaSzG^s9FT1H(FLlJOXK!51=g(#=EsA'
    'j9rfGB}3y(bm~g@_?n@)F5U{{sFeFuZ_|8{SG+E){W-k-+%toU;g#C-zPkbN%hJ27L1j@qMj}7UPGwGwvy!4kKpeN;EVdz0A9hXC%NQtu>%r'
    'E*q*L!(4A!5g_E@OVm}#OQ3&uQ%ORjQ7D?UDt0tYZrDWTwpC70#(H|tNP(NMxToQ=SJ%KywTMX=tXg(qq1bB$r9xhHOt&rtL^N~Gs%bDyWoW'
    'Vn4qmVE9V6?b1#u7qZSNDggCrWH~zb194A7Ix<$(pLCR%XrJC>)$k@nk={StynSUtcwV<aXD;hB$zU6j?^fhT2TEdgVwc*?z`vDug%r`9%8L'
    'iMi4&@wml?eslgXv)0t+&c}(lH@;Hl{3BtSI8FkVoUsbe*l^U+t{y@t21n$B9t=XZrYmX{4C(j}2$hSTEfsu_tP>Co^B^d=DFgNQ@Bag#$P~'
    '-'
)

def parse_args():
    dry="--dry-run" in sys.argv[1:]
    other=[a for a in sys.argv[1:] if a!="--dry-run"]
    if len(other)>1: raise ValueError("Use one optional web-directory argument")
    return pathlib.Path(other[0] if other else ".").expanduser().resolve(),dry

def main():
    base,dry=parse_args()
    print("FIGHT ROYALE V28 — ROXY AI + GUARD FATIGUE HUD + ROSTER BALANCE |",base)
    operations=json.loads(zlib.decompress(base64.b85decode("".join(PAYLOAD))).decode("utf-8"))
    paths=sorted({x[0] for x in operations})
    original={}; changed={}
    # Validate all files, all anchors, and version requirements BEFORE any write.
    for rel in paths:
        f=base/"src"/rel
        if not f.is_file(): raise RuntimeError("Missing " + str(f))
        data=f.read_text(encoding="utf-8-sig")
        if MARK in data: raise RuntimeError("V28 already installed in " + rel + "; no files changed")
        original[rel]=data
        changed[rel]=data
    if "GUARD_FATIGUE_V26" not in original["game/fighter.ts"] or        "ZEPHYR_DRAGON_DANCER_V1" not in original["game/fighter.ts"]:
        raise RuntimeError("Expected your V27 game source. No files changed; upload latest src ZIP if this differs.")
    for rel,old,new,count in operations:
        hits=changed[rel].count(old)
        if hits!=count:
            raise RuntimeError(f"{rel}: expected {count} matching anchor(s), got {hits}: {old[:90]!r}. No files changed; upload latest src ZIP for adaptation.")
        changed[rel]=changed[rel].replace(old,new,count)
    changed["game/ai.ts"]="// "+MARK+"\n"+changed["game/ai.ts"]
    if dry:
        for rel in paths: print("  WOULD update", "src/"+rel)
        print("Dry run complete. No files changed.")
        return 0
    stamp=datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup=base/".fight-royale-backups"/("v28-"+stamp)
    # Stage all files before replacing any of them.
    staged=[]; written=[]
    try:
        for rel in paths:
            dest=base/"src"/rel
            b=backup/"src"/rel
            b.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(dest,b)
            fd,temp=tempfile.mkstemp(prefix=".v28-",suffix=".tmp",dir=str(dest.parent))
            with os.fdopen(fd,"w",encoding="utf-8",newline="") as stream:
                stream.write(changed[rel])
            staged.append((dest,temp,rel))
        for dest,temp,rel in staged:
            os.replace(temp,dest)
            written.append((dest,rel))
            print("  updated src/"+rel)
    except Exception:
        for dest,rel in reversed(written):
            try: shutil.copy2(backup/"src"/rel,dest)
            except Exception: pass
        raise
    finally:
        for _,temp,_ in staged:
            try: os.unlink(temp)
            except FileNotFoundError: pass
    print("V28 installed. Backup:",backup)
    print("Run: npx tsc --noEmit -p . && npm run dev")
    print("Aster + Marina defense, Ember flames, Zarek air combo, Roxy Z AI and HUD updated.")
    return 0

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as e:
        print("ERROR:",e,file=sys.stderr)
        sys.exit(1)

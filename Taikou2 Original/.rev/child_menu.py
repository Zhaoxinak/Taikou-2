# -*- coding: utf8 -*-
"""
child_menu.py —— M3c 回家菜单「培养孩子」(x86 32 位, keystone 装配 + capstone 回读自检)

两块桩 + 一份只读数据, 全部落在 MOD 私有区:
  A) cm_hook   : 断点 0x4CD563 (回家菜单构建器 0x4CD480 弹菜单前) —— 把原生的
                 "码表 + 串指针数组"两份都拷进 MOD 区, 尾追第 7 项"培养孩子", 再按原生
                 约定 call 0x47BED0, 自己把返回的"序号"翻译成"指令码"(原生 0..6 / MOD 7 / 取消 -1),
                 最后逐条复刻原生收尾 pop edi/esi/ebp + add esp,0x24 + ret。
  B) cm_foster : 码 7 的处理程序, 挂在跳转表第 8 槽 (0x4CD47C 原为对齐 NOP)。
                 流程 = 选孩子(运行时拼姓名, **分页**: 一页 PAGE_KIDS 个 + 下一页/上一页) -> 选活动 -> 选教席
                 -> 选书籍档次 -> 写 CMD_RING 条目 + tail++。
                 两个分页埋点: PAGE_ROWS = 最近一次弹窗的行数(取最大值, >PAGE_KIDS 即导航行已出现),
                               PAGE_NAV  = 下一页/上一页被点的次数 (默认档 fam13 恒 0 => 没翻页发生过)。

为什么必须拷表: 原生栈上串指针数组 base=E-0x18 只有 E-0x18..E 这 24B (6 个指针), **第 7 个指针正好覆写返回地址**;
码表 base=E-0x24 的第 7 个 word 又落在 E-0x18 = ptr[0] 上 —— 两处都装不下第 7 项
(PLAN §8.1 栈容量硬约束) ⇒ 两份都搬出到 MOD 区, 且绕开 0x4CD583 的原生翻译。

引擎侧原语 (逐条实测, 见 PLAN_CHILD_RAISING.md §8.1):
  0x47BED0(count, dword* 串指针数组, flag, 0, 0) cdecl / 5 push / add esp,0x14
         -> ax = 选中序号, 0xffff = 取消。**内部 0x47BE00 限 count 为 1..12** (0x47BE0E `cmp di,0xc/jg`)
            —— 40 只是 0x47BED0 的拷贝钳位, 真正一屏最多 12 项。独立子菜单实测用 flag=4 (见 0x445758/0x412E64)。
  0x49A5C0(ecx=实体) -> eax=虚岁 (只吃 ecx; eax 被当成 16 位累加用, 高 16 位不可信 => 一律 movzx eax,ax)
  回家菜单循环头 0x4CD339 / 退出 0x4CD455; 构建器帧 E: 码表=E-0x24, 串指针数组=E-0x18, 计数在 edi。
  钩站点 0x4CD563 上的活寄存器 (从 exe 字节读出): ecx=flag(2|4) edx=串表基址 edi=项数 ebx=探病 gate 值。
  构建器返回后调用方先做两判断 (0x4CD36F `cmp ax,0xffff` / 0x4CD381 `cmp ax,4` -> 0x4CD41D),
  才 `movsx eax,ax; cmp eax,6; ja 0x4CD455; jmp [eax*4+0x4CD460]` —— 所以我们只有码 7 一条新路径,
  取消仍交回 -1 (走 ax==0xffff), 原生码 0..6 逐字不变 (码 4 压根到不了表)。

串/表极性提醒: 运行时 0x547C00=**名**表(sur_va), 0x549800=**姓**表(giv_va), 每条 7B (oid==槽 索引)。

★ 已修 bug (2026-10-07, fix3): cm_same 块里 edi 曾一身兼两职 ——
  273/275 行把 edi 当**行索引 row**(0..page_max-1) 写 sub_ptr/slot_arr 两张表,
  而 283/300 行的 `mov byte ptr [edi], al` 又把 edi 当**写指针**往里拷姓名。
  row==0 时 edi==0 ⇒ 往地址 0 写 ⇒ 点「培养孩子」必崩 (AV @ MOD+0x5ACE, EDI=0)。
  edx 在 271 行已经算好 `name_buf + row*24` 却没人拿它当游标。
  修法: 在 275 行之后、进姓名拷贝循环之前补一条 `mov edi, edx`, 让 edi 转为本行缓冲写游标
  (后面 291/300/308/322 那些 mov byte ptr [edi] 跟着一起变正确)。
"""

import os

import child_growth as CG

# ================= 补丁站点 (VA 与原始字节, 构建与验收共用) =================
HOOK_MENU_SITE = 0x4CD563        # 回家菜单构建器 0x4CD480 内, push ecx / push edx / push edi + call 前 2 字节
HOOK_MENU_ORIG = bytes.fromhex('515257E865')
CODE_LIMIT_SITE = 0x4CD390       # `cmp eax, 6` 的立即数 -> 8 (让码 7/8 不再是"越界即退出")
CODE_LIMIT_ORIG = b'\x06'
TABLE8_SITE = 0x4CD47C           # 跳转表第 8 槽 (表尾后的 4 字节对齐 NOP, 全镜像 0 引用)
TABLE8_ORIG = b'\x90\x90\x90\x90'
DISPATCH_SITE = 0x4CD38E         # `cmp eax, 7` 前 5 字节 (用于插入 item 8 的特判)
DISPATCH_ORIG = bytes.fromhex('83F8070F87')  # `cmp eax, 7; ja ...`
MENU_TOP = 0x4CD339              # 回家菜单循环头 (处理程序完事跳这里 = 重弹菜单)
MENU_EXIT = 0x4CD455             # 回家菜单退出 (leave)
MENU_CALL = 0x4CD367             # 循环里 call 构建器 0x4CD480 的位置
MENU_PRE_EXIT = 0x4CD41D         # 调用方预判: ax==0xffff(取消) 或 ax==4(离开) 直去这里, 不查表
DIALOG = 0x47BED0
AGE_GET = 0x49A5C0
CODE_STR_TAB = 0x50CAE8          # 原生菜单串表: 标签地址 = CODE_STR_TAB + 码*CODE_STR_STRIDE
CODE_STR_STRIDE = 11
# 构建器 0x4CD480 实际会写的指令码 (逐条从 exe 字节读出):
#   码 0 休息(恒有, 0x4CD49B 立即数) / 码 1 金库(0x4CD4A9 `mov word[esp+0xe], di`, 寄存器形式;
#     门 `test cl,4` = byte[0x516638]&4 **置位则整条消失且 edi 停在 1**) /
#   码 2 与宁宁交谈 或 码 6 与阿桢谈话((word[0x520604]>>12)&3 = 0/1; =2/3 时连 edi 都不加) /
#   码 3 武将休息室(gate=[E+4]) / 码 5 探病(gate=[E+8]) / 码 4 离开(恒有)
#   ⚠ 只按"store 立即数"扫会漏掉码 1 (它是 di 寄存器搬过去的) —— 这条已踩过一次。
#   => 项数 1..6, 我们追加 1 项 => 弹窗最多 7 项, 仍低于 12 硬门。
HOME_ITEM_MAX = 6                # 原生回家菜单本构建器最多 6 项 (0/1/2|6/3/5/4)
MENU_ITEM_MAX = 12               # 0x47BE00 的 count 上限: `test di,di/jle` + `cmp di,0xc/jg` 都直跳
                                 #   0x47BE8A `or ax,0xffff` —— **count>12 连窗口都不建, 等于没反应**
                                 #   (全镜像 107 个调用点自己就压在 2..11, 没有一处超)
PAGE_KIDS = int(os.environ.get('TKID_PAGE_KIDS', '10'))   # 一级"选孩子"每页孩子数; 尾追 下一页/上一页 ⇒ +2 = 12 正好顶门
                                                          # 构建时可用 TKID_PAGE_KIDS=2 造"分页试演档"(fam13 一城最多 6 个孩子,
                                                          # 默认 10 永远不生成导航行 => 没法手测翻页); 默认档行为逐字节不变
assert 1 <= PAGE_KIDS and PAGE_KIDS + 2 <= MENU_ITEM_MAX, '分页后一项都不能超 12 硬门'


def cap_imm(v):
    """capstone 把 <10 的立即数渲染成**十进制**(>=10 才 0x), 回读断言必须按同一套渲染比"""
    return '%d' % v if v < 10 else '0x%x' % v
NAME_ROW = 24                    # 孩子姓名行字节
STR_ROW = 24                     # 串池每项字节

AGE_GET_MASK = 0x63              # 标签里年龄钳到 99

# 串池槽位 (每项 STR_ROW 字节, GBK + NUL)
#   ★ 这一池 24 项把 MENU_STR 区 0x240 用满, 且下游 DEC100/NAME_BUF/... 紧排无余量
#     => 新增菜单项**不进这池**: 「生孩子」标签落在生孩子私有区尾部的独立 24B 行 (BIRTH_LABEL)。
S_HOME = 0                       # 培养孩子 (回家菜单第 7 项)
S_ACT0 = 1                       # 1..10 活动
S_TEACH0 = 11                    # 11..15 教席
S_TIER0 = 16                     # 16..19 书籍档次
S_BACK = 20                      # 暂不培养 (子菜单尾项 = 退出)
S_AGE_SUFFIX = 21                # "岁"
S_PREV = 22                      # 上一页 (一级选孩子的分页导航, 只有需要时才挂)
S_NEXT = 23                      # 下一页
STR_N = 24

TIER_NAMES = ('不用书籍', '普通书籍', '良好书籍', '名品书籍')

# ================= M5 (2026-10-07): 门禁 / 确认 / 反馈 串池 =================
#   为什么另开一池: MENU_STR 的 24 项已经把 0x240 用满, 扩容会顺移后面九个数据区的地址
#   (DEC100/NAME_BUF/SLOT_ARR/... /KD_CODE), 风险与收益不成比例; 独立池落在 MOD 区尾部。
#   ★ 每条 = MS_STR_ROW 字节, 布局 [GBK][NUL][pad] —— **没有长度前缀**:
#     ① 原生对话框 0x47BED0 收的是 C 字符串指针, 串首塞长度字节会把它显示成乱码;
#     ② 反馈小框 kd_m_frame **自己数到 NUL** 再传显式 cbString (本机 TextOutA 传 -1 一个字都不画)。
#     (kid_panel 自己那套池是 [len][GBK][NUL] 紧凑排列, 两边格式不同, 别照抄解码方式。)
MS_STR_ROW = 24
_COST_LINES = tuple(u'%s：%d天/%d文' % (nm, CG.ACT_DAYS[i], CG.ACT_DAYS[i] * CG.GOLD_PER_DAY)
                    for i, (nm, _d, _b) in enumerate(CG.ACTS))
MSG_STRINGS = (
    # 0..2 门禁拒绝 (单按钮提示框)
    u'这个月已经培养过了', u'所持金不足', u'本月时日无多',
    # 3..4 确认框
    u'就这么办', u'再想想',
    # 5..14 反馈台词: **与 child_growth.ACTS 同序** (反馈小框 = 孩子名 + 这一句)
    u'书本上的道理，我记住了', u'兵书真有意思', u'剑术练得手都酸了',
    u'礼数我会好好学的', u'茶道很雅致呢', u'算术好难啊',
    u'打工挣到钱了', u'铁炮的声音真响', u'跟着父亲学到好多', u'寺里修行很清苦',
    # 15 反馈小框底部提示
    u'点击关闭',
) + _COST_LINES                      # 16..25: 每条活动的天数/花费, 确认框第一行显示它
# ★ 26: 一个孩子都扫不到时的明说。原来是静默 return —— 玩家只看到"点了没反应",
#   连"是没孩子"还是"门禁拦了"都分不出来 (2026-10-07 那两轮实机反馈都卡在这个歧义上)。
MS_DENY_MONTH, MS_DENY_GOLD, MS_DENY_TIME = 0, 1, 2
MS_OK, MS_CANCEL = 3, 4
MS_LINE0, MS_MSG_HINT = 5, 15
MS_COST0 = 16                        # 费用提示首条下标; 与 ACTS 同序, 行地址 = 池首 + (MS_COST0+act)*24
MS_NONE = MS_COST0 + len(CG.ACTS)    # 26: "此城还没有可培养的孩子" (首屏为空时才弹)
MSG_STRINGS = MSG_STRINGS + (u'此城还没有可培养的孩子',)
MS_NO_SLOT = MS_NONE + 1             # 27: 生孩子扫不到空槽/空身份键 (满员) 的明说
MSG_STRINGS = MSG_STRINGS + (u'已经没有空位了',)
# ★ 28..30: 出生提示 (2026-10-07 实机反馈「我生了孩子后, 没有任何的提示」)。
#   原来办完事直接 jmp 收尾, 玩家看不到"到底生了没有" => 必须显式确认, 并把孩子姓名读回来
#   (姓行 + 名行 拼成的连续串显示在第 2 行)。
MS_BORN = MS_NO_SLOT + 1             # 28: 提示标题
MSG_STRINGS = MSG_STRINGS + (u'孩子出生了',)
MS_BORN_AT = MS_BORN + 1             # 29: 说明他跟着父亲住在哪
MSG_STRINGS = MSG_STRINGS + (u'他随父亲住在本城',)
# ★ 30: 为什么城里的武将列表看不到他 —— 原生就是这样的 (武将列表走本城家臣链,
#   只有元服时 0x4A0540 才把人挂进链; 见 .rev/_list_probe_report.md)。不写清就会被当成 bug。
MS_BORN_GK = MS_BORN_AT + 1
MSG_STRINGS = MSG_STRINGS + (u'元服后进入武将列表',)
assert len(MSG_STRINGS) == MS_BORN_GK + 1, (len(MSG_STRINGS), MS_BORN_GK)
assert MS_STR_ROW * len(MSG_STRINGS) <= 0x300, 'MSG_STR 池吃掉 FOSTER 前的全部余量'
assert MS_COST0 == MS_MSG_HINT + 1, (MS_COST0, MS_MSG_HINT)


# ================= 生孩子: 预选名字列表 =================
# 回家菜单第 8 项的标签 (不进 MENU_STR 那 24 行的池, 见上面的槽位说明)
BIRTH_LABEL = u'生孩子'


def birth_label_bytes():
    """生孩子菜单标签: 一行 STR_ROW 字节的 C 字符串 (GBK + NUL + pad)"""
    b = BIRTH_LABEL.encode('gbk')
    assert len(b) + 1 <= STR_ROW, b
    return b + b'\x00' * (STR_ROW - len(b))


# 名字池: 游戏没有键盘输入, 只能预置。这里放 **500 个真实日本名**(男 405 + 女 95,
#   每 4 个男名后插 1 个女名 => 选择框每一页都有女性名), 每次开框只供 BIRTH_NAME_OFFER 个,
#   选过的记进 USED 永不重发, 且与**游戏内在世人物的名**自动避让 (bn_avail/bn_live 在运行时筛)。
#   名单来源/审查见 .rev/_names_draft.py (603 候选 -> 去重 600 -> 砍 100 个生僻尾名 = 500)。
# 每行 7B = 最多 6B GBK(3 汉字) + NUL, 所以长度硬门是 3 个汉字。
BIRTH_NAMES = (
    u'信长', u'信忠', u'信雄', u'信孝', u'阿市', u'信秀', u'信胜', u'信包', u'信澄', u'阿松',
    u'信广', u'信定', u'长则', u'长益', u'阿茶', u'胜家', u'胜丰', u'胜政', u'胜俊', u'阿静',
    u'胜以', u'吉胜', u'胜重', u'胜吉', u'阿菊', u'辉政', u'恒兴', u'忠继', u'元光', u'阿虎',
    u'长泰', u'由之', u'胜入', u'宗二', u'阿初', u'光秀', u'光忠', u'元智', u'秀满', u'阿江',
    u'光胜', u'朝景', u'光家', u'秀有', u'阿督', u'长秀', u'氏秀', u'长重', u'长遗', u'阿完',
    u'秀政', u'秀治', u'利家', u'利长', u'阿胜', u'利常', u'利玄', u'利春', u'利久', u'阿万',
    u'庆次', u'利庆', u'利孝', u'盛政', u'阿龟', u'正胜', u'安政', u'信治', u'盛之', u'阿梅',
    u'一益', u'贞胜', u'具益', u'秀正', u'阿兰', u'良通', u'贞通', u'重通', u'通之', u'阿竹',
    u'清秀', u'重政', u'藤孝', u'忠兴', u'阿桂', u'赖尚', u'忠利', u'秀吉', u'秀长', u'阿樱',
    u'秀胜', u'秀保', u'秀秋', u'秀宗', u'阿雪', u'秀包', u'秀次', u'秀赖', u'吉治', u'阿月',
    u'长吉', u'秀俊', u'定久', u'定利', u'阿春', u'利定', u'吉亲', u'木吉', u'秀房', u'阿佐',
    u'吉房', u'久吉', u'小一郎', u'鹤松', u'阿通', u'清正', u'光泰', u'嘉明', u'忠广', u'阿爱',
    u'明成', u'雅量', u'正则', u'高政', u'阿都', u'广纲', u'正之', u'家政', u'至家', u'阿古',
    u'家利', u'小六', u'秀重', u'弘就', u'阿六', u'孝高', u'长政', u'直之', u'利之', u'阿十',
    u'之由', u'长兴', u'高次', u'高通', u'阿八', u'高清', u'高珍', u'三成', u'家继', u'阿世',
    u'重家', u'正澄', u'家俊', u'行长', u'宁宁', u'隆康', u'重成', u'宜朝', u'正家', u'茶茶',
    u'正氏', u'氏信', u'元存', u'且元', u'小督', u'孝贞', u'盛重', u'长盛', u'利政', u'见松',
    u'俊次', u'盛次', u'幸长', u'幸贞', u'于大', u'长之', u'幸一', u'一氏', u'一正', u'千代',
    u'重次', u'亲重', u'高吉', u'俊胜', u'五德', u'亲澄', u'安国', u'直泰', u'家康', u'见月',
    u'秀忠', u'家光', u'家纲', u'信康', u'世恋', u'忠吉', u'忠胜', u'忠直', u'家成', u'五郎八',
    u'家亲', u'家忠', u'家清', u'康亲', u'初', u'康长', u'康继', u'康直', u'清康', u'江',
    u'广忠', u'元康', u'昌久', u'定积', u'完', u'信光', u'亲长', u'亲忠', u'康俊', u'督',
    u'长亲', u'忠昌', u'忠良', u'光普', u'胜', u'家正', u'忠克', u'忠弘', u'信纲', u'市',
    u'光重', u'定纲', u'齐裕', u'纲重', u'久', u'忠教', u'忠年', u'康昭', u'直政', u'万',
    u'直孝', u'直继', u'直宗', u'直盛', u'龟', u'直亲', u'直亮', u'直澄', u'直时', u'鹤',
    u'好直', u'忠政', u'正纯', u'正信', u'铃', u'康纪', u'尚广', u'平八', u'重忠', u'琴',
    u'忠真', u'忠义', u'利忠', u'以忠', u'操', u'政朝', u'忠平', u'正利', u'忠次', u'枫',
    u'家次', u'忠世', u'忠清', u'家业', u'莲', u'忠景', u'数正', u'家重', u'康家', u'政子',
    u'氏家', u'康政', u'康种', u'政近', u'昌子', u'正成', u'半藏', u'就正', u'忠邻', u'清子',
    u'长安', u'忠为', u'秀兴', u'政清', u'幸子', u'正重', u'元忠', u'元臣', u'贞宗', u'德子',
    u'康景', u'信玄', u'义信', u'胜赖', u'光子', u'信繁', u'信赖', u'信虎', u'晴信', u'直子',
    u'信廉', u'信丰', u'信满', u'信之', u'爱子', u'虎纲', u'昌景', u'房守', u'昌丰', u'敏子',
    u'虎胤', u'虎盛', u'虎泰', u'虎昌', u'静子', u'幸隆', u'昌幸', u'幸村', u'信幸', u'贞子',
    u'大助', u'高信', u'胜沼', u'信守', u'惠子', u'满幸', u'基胜', u'景信', u'辉虎', u'良子',
    u'政虎', u'景胜', u'定胜', u'宪政', u'弘子', u'房实', u'定实', u'显家', u'勘助', u'稙子',
    u'定满', u'景广', u'宪房', u'兼续', u'氏子', u'光实', u'弥太郎', u'重房', u'宪定', u'义子',
    u'胜实', u'辉定', u'景宪', u'氏时', u'长子', u'氏纲', u'氏康', u'氏政', u'氏直', u'景子',
    u'氏照', u'氏邦', u'氏规', u'宪盛', u'胜子', u'宪秀', u'纲景', u'定冈', u'氏房', u'春子',
    u'氏治', u'氏定', u'氏澄', u'氏一', u'夏子', u'义元', u'氏亲', u'义直', u'义康', u'秋子',
    u'范忠', u'氏峰', u'雪斋', u'氏资', u'冬子', u'义均', u'氏廉', u'道三', u'义龙', u'梅子',
    u'龙兴', u'利尧', u'利三', u'藤高', u'竹子', u'义效', u'光氏', u'尧之', u'高光', u'菊子',
    u'宗滴', u'义景', u'敏景', u'贞景', u'松子', u'景丰', u'教景', u'景范', u'繁景', u'桃子',
    u'持景', u'宗淳', u'久政', u'秀久', u'樱子', u'政家', u'万吉', u'景继', u'高景', u'兰子',
    u'元就', u'隆元', u'辉元', u'秀元', u'鹤子', u'元春', u'元清', u'元相', u'广家', u'铃子',
    u'元胜', u'就胜', u'房家', u'就兴', u'琴子', u'元氏', u'就实', u'方实', u'就昭', u'秀子',
    u'隆景', u'元苗', u'惠琼', u'元知', u'完子', u'春元', u'元房', u'国元', u'经元', u'督子',
    u'经久', u'晴久', u'义久', u'幸久', u'初子', u'盛久', u'丰国', u'氏清', u'幸盛', u'江子',
    u'秀纲', u'久纲', u'义祐', u'宗景', u'万子', u'长治', u'良赖', u'澄久', u'义春', u'国久',
    u'元有', u'高久', u'久幸', u'义镇', u'义统', u'鉴连', u'道雪', u'宗茂', u'统虎', u'绍运',
    u'隆信', u'辉宗', u'政宗', u'义光', u'元亲', u'元秋', u'久秀', u'基次', u'利休', u'织部',
)
assert len(BIRTH_NAMES) == 500, len(BIRTH_NAMES)
assert len(set(BIRTH_NAMES)) == len(BIRTH_NAMES), '名字池内有重复'
assert all(len(n.encode('gbk')) <= 6 for n in BIRTH_NAMES), '名字超 3 汉字'
BIRTH_NAME_COUNT = len(BIRTH_NAMES)
# 每次开框供 20 个 —— bn_avail 的起点由原生 rand 现取、扫到池尾绕回池头 (所以两次开框给的**不是同一批**),
#   收满 20 就停; 一页 PAGE_KIDS=10 行 + 1 行导航 = 11 行, 压在原生列表对话框 0x47BED0 的 12 项硬门里
#   => 20 个正好两页。
BIRTH_NAME_PAGE = PAGE_KIDS
BIRTH_NAME_OFFER = 20
assert BIRTH_NAME_OFFER % BIRTH_NAME_PAGE == 0, (BIRTH_NAME_OFFER, BIRTH_NAME_PAGE)
assert BIRTH_NAME_OFFER // BIRTH_NAME_PAGE + 1 <= 12, '一页最多 11 行(含导航)'
BIRTH_OID_MAX = 0x2BC                  # BSDATA 身份键上界 (0..0x2BB), 与 gen_oid_map/M1 同源


def birth_name_pool_bytes():
    """名字串池: 500 项 x 7 字节 (GBK + NUL)"""
    out = bytearray()
    for n in BIRTH_NAMES:
        b = n.encode('gbk')
        assert len(b) + 1 <= 7, ('名字行越界', n, len(b))
        out += b + b'\x00' * (7 - len(b))
    return bytes(out)


def msg_str_pool_bytes():
    out = bytearray()
    for s in MSG_STRINGS:
        b = s.encode('gbk')
        assert len(b) + 1 <= MS_STR_ROW, ('反馈串超行', s, len(b))
        out += b + b'\x00' * (MS_STR_ROW - len(b))
    return bytes(out)


def msg_str_va(str_va, i):
    return str_va + i * MS_STR_ROW


def str_items():
    """串池内容 (顺序即槽位)。活动/教席名一律从 child_growth 的表来, 不另立一份。"""
    it = [u'培养孩子']
    it += [u'%s·%s+%d%%' % (nm, CG.DIM_NAME[d], b) for nm, d, b in CG.ACTS]
    it += [u'%s+%d%%' % (nm, t) for nm, t in CG.TEACHERS]
    it += [u'%s+%d%%' % (nm, i * CG.B_TIER_STEP) for i, nm in enumerate(TIER_NAMES)]
    it += [u'暂不培养', u'岁', u'上一页', u'下一页']
    assert len(it) == STR_N, len(it)
    return it


def str_pool_bytes():
    out = bytearray()
    for s in str_items():
        b = s.encode('gbk')
        assert len(b) + 1 <= STR_ROW, ('菜单串超行', s, len(b))
        out += b + b'\x00' * (STR_ROW - len(b))     # 补齐整行 (含结束 NUL)
    return bytes(out)


def dec100_bytes():
    """DEC100[i*2] = 两位十进制 '00'..'99' —— 桩里按 age*2 直接取 2 字节, 免去除法。"""
    return ''.join('%02d' % i for i in range(100)).encode('ascii')


def submenu_ptr_bytes(str_va, first_slot, n_items):
    """静态子菜单指针数组: n_items 个选项串 + 1 个"暂不培养"。"""
    import struct
    v = [str_va + (first_slot + i) * STR_ROW for i in range(n_items)]
    v.append(str_va + S_BACK * STR_ROW)
    return struct.pack('<%dI' % len(v), *v)


def scratch_layout(scr_va):
    return {'s_ebx': scr_va, 's_flag': scr_va + 4, 's_cnt': scr_va + 8,
            's_ptrs': scr_va + 0x0C, 's_cnt1': scr_va + 0x10}


# ================= A) 回家菜单钩子 (断点 0x4CD563) =================
SRC_HOOK = """
cm_hook:
  mov dword ptr [%(s_ebx)s], ebx
  mov dword ptr [%(s_flag)s], ecx
  mov dword ptr [%(s_cnt)s], edi
  mov dword ptr [%(s_ptrs)s], edx
  inc dword ptr [%(c_menu)s]
  lea esi, [esp + 0x14]
  mov edi, %(menu_code)s
  mov ecx, dword ptr [%(s_cnt)s]
  test ecx, ecx
  je cm_ptr
cm_code_loop:
  mov ax, word ptr [esi]
  mov word ptr [edi], ax
  add esi, 2
  add edi, 2
  dec ecx
  jne cm_code_loop
cm_ptr:
  mov esi, dword ptr [%(s_ptrs)s]
  mov edi, %(menu_ptr)s
  mov ecx, dword ptr [%(s_cnt)s]
  test ecx, ecx
  je cm_append
cm_ptr_loop:
  mov eax, dword ptr [esi]
  mov dword ptr [edi], eax
  add esi, 4
  add edi, 4
  dec ecx
  jne cm_ptr_loop
cm_append:
  # 0x47BED0 arg1 = item count (edx=count, cmp ax,dx as copy bound), arg2 = string ptr array, arg3 = style
  # => last push = arg1 must be ecx(=cnt+2); pushing s_flag(style 2/4) last drew only 2 items, wrong style
  mov eax, dword ptr [%(s_cnt)s]
  lea ecx, [eax + 2]
  mov dword ptr [%(s_cnt1)s], ecx
  shl eax, 2
  mov edx, %(menu_ptr)s
  mov dword ptr [edx + eax], %(str_foster)s
  mov dword ptr [edx + eax + 4], %(str_birth)s
  push dword ptr [%(s_flag)s]
  push edx
  push ecx
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je cm_cancel
  movzx ecx, ax
  cmp cx, word ptr [%(s_cnt)s]
  je cm_foster
  dec cx
  cmp cx, word ptr [%(s_cnt)s]
  je cm_birth
  inc cx
  movzx eax, word ptr [ecx * 2 + %(menu_code)s]
  jmp cm_out
cm_foster:
  mov dword ptr [%(pick)s], 0
  mov eax, 7
  jmp cm_out
cm_birth:
  mov dword ptr [%(pick)s], 1
  mov eax, 7
  jmp cm_out
cm_cancel:
  mov eax, -1
cm_out:
  mov ebx, dword ptr [%(s_ebx)s]
  pop edi
  pop esi
  pop ebp
  add esp, 0x24
  ret
"""


# ================= C) 码 7 的第二条路: 生孩子流程 =================
# 帧: push ebx/ebp/esi/edi + sub esp,0x20
#   +0x00 L_LORD  主角实体指针 (= 进来的 esi)   +0x04 L_PAGE 名字页起点 (0 / PAGE_KIDS)
#   +0x08 L_ROWS  本页行数                     +0x0C L_NAME 选中的名字下标
#   +0x10 L_SLOT  选中的空槽                   +0x14 L_OID  选中的空身份键
#   +0x18 L_CITY  主角 国|城 (排程表项的静态兜底)
#   +0x1C L_FSLOT 主角自己的池槽 (= 排程表的 fslot, 也 = 主角姓行的索引)
#
#   ★ 池槽与 oid 是两个键空间, 别混: 排程表 fslot / 姓表行号 / 名表行号 = **槽**;
#     孩子的 +0x1d 父链 = **oid** (probe_keyspace: ent+0=槽号、ent+2=oid, 352/352)。
#
# ★ 实例化**不自己来**: 往 child_pass 的排程表尾追一条 (oid, slot, fslot=主角, 国|城), 然后
#   call child_pass。那条路是实机验证过的唯一配方 (INST + init_stats 五维减半 + bit15/bit7/
#   nibble 0xb/bit4/身分码 + 主君 0xffff + 登场标志 + place_child 随父居住 + 位图记账),
#   自己照抄一份等于把已经踩稳的坑再踩一次; 而且追进表以后这个孩子从此有月钩复臂、
#   成长结算、到龄元服, 不用再单独接。
SRC_BIRTH = """
cm_birth_handler:
  push ebx
  push ebp
  push esi
  push edi
  sub esp, 0x20
  inc dword ptr [%(c_birth)s]
  mov dword ptr [esp + 0x00], esi
  movzx eax, word ptr [esi + 0x24]
  mov dword ptr [esp + 0x18], eax
  movzx eax, word ptr [esi + 0x00]
  mov dword ptr [esp + 0x1c], eax
  mov dword ptr [esp + 0x04], 0
  # Before opening the box, collect the names this round may offer into AVAIL: skip the ones
  #   already picked (USED) and the ones a LIVING character in this scenario wears (bn_live
  #   walks every entity's given-name row). The scan starts at a NATIVE-RAND position and
  #   wraps, so opening the box twice in a row offers a DIFFERENT slice of 0x14 names
  #   (player's ask: "each time must be different"). ebp counts slots scanned => at most
  #   one full turn. Pool holds 0x1F4 real names, we stop at 0x14 => 0xA rows per page +
  #   1 nav row, inside the native list dialog's hard 0xC-row limit.
  call bn_avail
bn_page:
  xor edi, edi
bn_fill:
  mov eax, dword ptr [esp + 0x04]
  add eax, edi
  cmp eax, dword ptr [%(avail_n)s]
  jae bn_nav
  movzx eax, word ptr [eax * 2 + %(avail)s]
  lea edx, [eax * 8]
  sub edx, eax
  add edx, %(name_pool)s
  mov dword ptr [edi * 4 + %(sub_ptr)s], edx
  mov word ptr [edi * 2 + %(slot_arr)s], ax
  inc edi
  cmp edi, %(page_max)s
  jb bn_fill
bn_nav:
  cmp dword ptr [esp + 0x04], 0
  je bn_nav_next
  mov dword ptr [edi * 4 + %(sub_ptr)s], %(str_prev)s
  mov word ptr [edi * 2 + %(slot_arr)s], 0xFFFD
  jmp bn_show
bn_nav_next:
  mov eax, %(page_max)s
  add eax, dword ptr [esp + 0x04]
  cmp eax, dword ptr [%(avail_n)s]
  jae bn_show
  mov dword ptr [edi * 4 + %(sub_ptr)s], %(str_next)s
  mov word ptr [edi * 2 + %(slot_arr)s], 0xFFFE
bn_show:
  inc edi
  mov dword ptr [esp + 0x08], edi
  push 0
  push 0
  push 4
  push %(sub_ptr)s
  push edi
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je b_cancel
  movzx eax, ax
  movzx edx, word ptr [eax * 2 + %(slot_arr)s]
  cmp edx, 0xFFFE
  je bn_next
  cmp edx, 0xFFFD
  je bn_prev
  mov dword ptr [esp + 0x0C], edx
  # A picked name goes into USED so bn_avail never offers it again (player's own request).
  mov byte ptr [edx + %(used)s], 0x1
  jmp b_slot
bn_next:
  add dword ptr [esp + 0x04], %(page_max)s
  jmp bn_page
bn_prev:
  sub dword ptr [esp + 0x04], %(page_max)s
  jmp bn_page
b_slot:
  mov ebx, %(slot_lo)s
bs_loop:
  cmp ebx, %(cap)s
  jae b_none
  bt dword ptr [%(child_bm)s], ebx
  jc bs_next
  lea ecx, [ebx + ebx * 2]
  shl ecx, 4
  sub ecx, ebx
  add ecx, %(pool)s
  movzx edx, word ptr [ecx + 0x2c]
  and edx, 0x8080
  cmp edx, 0x8080
  jne bs_next
  mov dword ptr [esp + 0x10], ebx
  jmp b_oid
bs_next:
  inc ebx
  jmp bs_loop
b_oid:
  mov ebx, %(oid_hi)s
bo_loop:
  cmp ebx, 0
  jl b_none
  cmp byte ptr [ebx + %(flagtab)s], 0
  jne bo_next
  mov ecx, %(sched)s
bo_used:
  movzx eax, word ptr [ecx]
  cmp ax, 0xffff
  je bo_found
  cmp eax, ebx
  je bo_next
  add ecx, 8
  jmp bo_used
bo_next:
  dec ebx
  jmp bo_loop
bo_found:
  mov dword ptr [esp + 0x14], ebx
  mov ebx, %(sched)s
bse_loop:
  cmp ebx, %(sched_end)s
  jae b_none
  movzx eax, word ptr [ebx]
  cmp ax, 0xffff
  je bse_write
  add ebx, 8
  jmp bse_loop
bse_write:
  mov eax, dword ptr [esp + 0x14]
  mov word ptr [ebx], ax
  mov eax, dword ptr [esp + 0x10]
  mov word ptr [ebx + 2], ax
  mov eax, dword ptr [esp + 0x1c]
  mov word ptr [ebx + 4], ax
  mov eax, dword ptr [esp + 0x18]
  mov word ptr [ebx + 6], ax
  mov word ptr [ebx + 8], 0xFFFF
  call %(child_pass)s
  movzx ebx, word ptr [esp + 0x10]
  lea ecx, [ebx + ebx * 2]
  shl ecx, 4
  sub ecx, ebx
  add ecx, %(pool)s
  # virtual age 1: age = (year+0x618) - (([+0x1b]&0x7f)+0x5d2) + 1  =>  [+0x1b] = year + 0x46
  movzx eax, byte ptr [%(date_y)s]
  add eax, 0x46
  mov byte ptr [ecx + 0x1b], al
  # father link (+0x1d, and record+0x29 through it) is an OID, while the name tables are indexed
  #   by SLOT -- the two live in different key spaces (probe_keyspace: ent+0=slot, ent+2=oid).
  mov eax, dword ptr [esp + 0x00]
  movzx eax, word ptr [eax + 0x02]
  mov word ptr [ecx + 0x1d], ax
  # surname = the lord's row (surname table GIV, 7B per SLOT) -- INST copied the free oid's own
  #   surname, so it must be overwritten. Byte loop instead of rep movsb: we do not want to
  #   depend on the direction flag being clear.
  mov edx, dword ptr [esp + 0x1c]
  lea esi, [edx * 8]
  sub esi, edx
  add esi, %(giv)s
  lea edi, [ebx * 8]
  sub edi, ebx
  add edi, %(giv)s
  mov ecx, 7
bcp_sur:
  mov dl, byte ptr [esi]
  mov byte ptr [edi], dl
  inc esi
  inc edi
  dec ecx
  jne bcp_sur
  # given name = the row the player picked (given table SUR, 7B/slot; pool rows are NUL-padded)
  movzx ebx, word ptr [esp + 0x10]
  lea edi, [ebx * 8]
  sub edi, ebx
  add edi, %(sur)s
  movzx ecx, word ptr [esp + 0x0C]
  lea esi, [ecx * 8]
  sub esi, ecx
  add esi, %(name_pool)s
  mov ecx, 7
bcp_giv:
  mov dl, byte ptr [esi]
  mov byte ptr [edi], dl
  inc esi
  inc edi
  dec ecx
  jne bcp_giv
  # ---- birth confirmation box (real-machine report: "nothing at all happens, so I cannot
  #   so I cannot tell whether a child was born"). The surname/given rows are 7B each and
  #   NUL-padded, so the two rows cannot simply be concatenated -- the middle NUL truncates
  #   the C string. Compose one contiguous string first (max 6+6+1 = 13B into a 16B buffer),
  #   and read it back from the RUNTIME name tables so the box shows what really got stored.
  movzx ebx, word ptr [esp + 0x10]
  lea esi, [ebx * 8]
  sub esi, ebx
  add esi, %(giv)s
  mov edi, %(name_tmp)s
  mov ecx, 7
bp_sur:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  test al, al
  je bp_sur_end
  inc esi
  inc edi
  dec ecx
  jne bp_sur
bp_sur_end:
  mov byte ptr [edi], 0
  movzx ebx, word ptr [esp + 0x10]
  lea esi, [ebx * 8]
  sub esi, ebx
  add esi, %(sur)s
  mov ecx, 7
bp_giv:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  test al, al
  je bp_giv_end
  inc esi
  inc edi
  dec ecx
  jne bp_giv
bp_giv_end:
  mov byte ptr [edi], 0
  # four-row pointer array (title / name / lives-with-father / why-not-in-the-list) into the
  #   BIRTH_PROMPT area, then the native 5-arg dialog convention (count, ptr array, style, 0, 0).
  #   Row 4 answers the real-machine question "why is he not in the castle's retainer list":
  #   that list walks the castle's vassal CHAIN (only genpuku inserts a person into it,
  #   see _list_probe_report.md), so a child is absent by native design -- not a lost binding.
  mov dword ptr [%(msg_arr)s], %(born_str)s
  mov dword ptr [%(msg_arr)s + 4], %(name_tmp)s
  mov dword ptr [%(msg_arr)s + 8], %(born_at)s
  mov dword ptr [%(msg_arr)s + 0xC], %(born_gk)s
  push 0
  push 0
  push 4
  push %(msg_arr)s
  push 4
  call %(dialog)s
  add esp, 0x14
  jmp b_cancel
b_none:
  push 0
  push 0
  push 4
  push %(str_none)s
  push 1
  call %(dialog)s
  add esp, 0x14
b_cancel:
  add esp, 0x20
  pop edi
  pop esi
  pop ebp
  pop ebx
  jmp %(menu_top)s
bn_avail:
  # in: nothing; fills AVAIL with up to OFFER pool indices and AVAIL_N with how many.
  #   Native rand 0x4EBD60(n) -> 0..n-1 (cdecl, clobbers only eax/edx) gives a RANDOM START
  #   and the scan wraps, so every opening of the box offers a different slice of the pool.
  #   ebp = slots scanned (bounded by one full turn => we cannot spin forever even when the
  #   pool runs dry, e.g. after the player has picked hundreds of them). Only
  #   ebx/eax/edx/ecx/ebp are touched -- ebx/ebp are pushed by the handler, and ecx holds
  #   the pool row for bn_live.
  mov dword ptr [%(avail_n)s], 0
  xor ebp, ebp
  push %(count)s
  call %(rand)s
  add esp, 4
  mov ebx, eax
ba_loop:
  cmp ebp, %(count)s
  jae ba_done
  inc ebp
  mov eax, dword ptr [%(avail_n)s]
  cmp eax, %(offer)s
  jae ba_done
  cmp byte ptr [ebx + %(used)s], 0
  jne ba_next
  lea ecx, [ebx * 8]
  sub ecx, ebx
  add ecx, %(name_pool)s
  call bn_live
  test eax, eax
  jne ba_next
  mov eax, dword ptr [%(avail_n)s]
  mov word ptr [eax * 2 + %(avail)s], bx
  inc dword ptr [%(avail_n)s]
ba_next:
  inc ebx
  cmp ebx, %(count)s
  jb ba_loop
  xor ebx, ebx
  jmp ba_loop
ba_done:
  ret
bn_live:
  # in: ecx = the pool row (7 bytes); out: eax = 1 somebody wears it / 0 the name is free.
  #   The on-duty test is the SAME three-branch gate the dynamic family-tree stub uses
  #   (tree_dyn): adult 0x8080, child 0x001B, post-genpuku 0x010F -- mask 0x879F strips the
  #   castle-lord bits, so 0x081B (a child who is already head of house) counts too.
  #   Touches eax/edx/esi/edi only, keeping the caller's ebx and the ecx argument alive.
  xor esi, esi
bl_loop:
  cmp esi, %(cap)s
  jae bl_free
  lea eax, [esi + esi * 2]
  shl eax, 4
  sub eax, esi
  add eax, %(pool)s
  movzx edx, word ptr [eax + 0x2c]
  mov eax, edx
  and eax, 0x8080
  cmp eax, 0x8080
  je bl_same
  and edx, 0x879F
  cmp edx, 0x001B
  je bl_same
  cmp edx, 0x010F
  jne bl_next
bl_same:
  lea edi, [esi * 8]
  sub edi, esi
  add edi, %(sur)s
  # Whole-row compare: dword at +0 covers bytes 0-3 and dword at +3 covers 3-6, so seven
  #   bytes get checked with two reads. Both rows are NUL-padded, so equality == same name.
  mov eax, dword ptr [ecx]
  cmp eax, dword ptr [edi]
  jne bl_next
  mov eax, dword ptr [ecx + 3]
  cmp eax, dword ptr [edi + 3]
  jne bl_next
  mov eax, 0x1
  ret
bl_next:
  inc esi
  jmp bl_loop
bl_free:
  xor eax, eax
  ret
"""


# ================= B) 码 7 处理程序: 培养孩子流程 =================
# 帧: push ebx/ebp/esi/edi (收尾原样 pop, 回 0x4CD339 时循环状态与进来时一致) + sub esp,0x38
#   +0x00 L_LORD  主角实体指针 (= 进来的 esi)
#   +0x04 L_CITY  主角 国|城 (实体 +0x24 的 word)
#   +0x08 L_CUR   槽游标 0..CAP
#   +0x0C L_ROWS  本页已收的孩子行数 (< PAGE_KIDS)
#   +0x10 L_ENT   选中孩子实体指针
#   +0x14 L_SLOT  选中孩子槽
#   +0x18 L_ACT / +0x1C L_TEACH / +0x20 L_TIER
#   +0x24 L_CURS  姓名行写指针   +0x28 L_TMP
#   +0x2C L_START 本页起点 = 已跳过多少个同城孩子 (0 基, 每页加 PAGE_KIDS; 不用乘法所以也没有除法)
#   +0x30 L_MATCH 本次扫描累计的同城孩子数 (整池, 不限页) => 有没有下一页就看它
#   +0x34 备用 (导航不靠行号判定: 行号在"只有上一页/只有下一页"时会撞车, 所以把哨兵写进行表)
SRC_FOSTER = """
cm_foster:
  # Code 7 has only ONE table slot (0x4CD47C; slot 8 would be 0x4CD480 = the builder's own
  #   prologue), so the appended birth row does not get a code of its own: the hook records
  #   which row was picked in BIRTH_PICK and we route here.
  #   Routing must happen at the DISPATCHER level, not by jmp-ing out of the hook --
  #   inside the hook we still stand on the builder's frame (sub esp,0x24 + push ebp/esi/edi
  #   + return address = 0x34 bytes not unwound), so jmp-ing from there tilts the caller's
  #   esp and the return address on its stack => AV on leaving the home menu.
  cmp dword ptr [%(pick)s], 0
  je cm_foster_body
  jmp %(birth_handler)s
cm_foster_body:
  push ebx
  push ebp
  push esi
  push edi
  sub esp, 0x38
  inc dword ptr [%(c_panel)s]
  mov dword ptr [esp + 0x00], esi
  movzx eax, word ptr [esi + 0x24]
  mov dword ptr [esp + 0x04], eax
  # M5b (real-machine report: "after entering a castle and going home the child list is
  #   empty, and it only comes back the next month"): the same-city filter below compares the child's word[+0x24] with the player's, but child_stub.place_child
  #   (live-with-father) only runs from make_child and the MONTHLY rearm -- so right after the player
  #   moves the children still carry the OLD city and the list comes up empty until the next
  #   month hook. child_pass is a fully self-contained, idempotent table loop (it pushes/pops
  #   ebx/esi/edi/ebp itself) whose rearm path ends in place_child, so calling it here makes the
  #   roster always reflect where the fathers are right now.
  call %(child_pass)s
  xor eax, eax
  mov dword ptr [esp + 0x08], eax
  mov dword ptr [esp + 0x0C], eax
  mov dword ptr [esp + 0x2C], eax
  mov dword ptr [esp + 0x30], eax
cm_page:
  mov dword ptr [esp + 0x08], 0
  mov dword ptr [esp + 0x0C], 0
  mov dword ptr [esp + 0x30], 0
cm_scan:
  mov eax, dword ptr [esp + 0x08]
  cmp eax, %(cap)s
  jae cm_scan_end
  inc dword ptr [esp + 0x08]
  mov ecx, eax
  shr ecx, 3
  movzx edx, byte ptr [ecx + %(bm)s]
  and ecx, 7
  bt edx, ecx
  jnc cm_scan
  lea ecx, [eax + eax * 2]
  shl ecx, 4
  sub ecx, eax
  add ecx, %(pool)s
  movzx edx, byte ptr [ecx + 0x2C]
  and dl, 0x0F
  cmp dl, 0xb
  jne cm_scan
  test byte ptr [ecx + 0x2D], 0x80
  jnz cm_scan
  movzx edx, word ptr [ecx + 0x24]
  cmp dx, word ptr [esp + 0x04]
  je cm_same
  inc dword ptr [%(c_notcity)s]
  jmp cm_scan
cm_same:
  mov eax, dword ptr [esp + 0x30]
  cmp eax, dword ptr [esp + 0x2C]
  jb cm_count
  cmp dword ptr [esp + 0x0C], %(page_max)s
  jae cm_count
  mov eax, dword ptr [esp + 0x08]
  dec eax
  mov dword ptr [esp + 0x10], ecx
  mov dword ptr [esp + 0x14], eax
  mov edi, dword ptr [esp + 0x0C]
  lea edx, [edi + edi * 2]
  shl edx, 3
  add edx, %(name_buf)s
  mov dword ptr [esp + 0x24], edx
  mov dword ptr [edi * 4 + %(sub_ptr)s], edx
  movzx eax, word ptr [esp + 0x14]
  mov word ptr [edi * 2 + %(slot_arr)s], ax
  mov edi, edx
  mov esi, eax
  shl esi, 3
  sub esi, eax
  add esi, %(giv)s
  mov ecx, 7
cm_cp_surname:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  test al, al
  je cm_cp_surname_end
  inc esi
  inc edi
  dec ecx
  jne cm_cp_surname
cm_cp_surname_end:
  mov byte ptr [edi], 0
  mov eax, dword ptr [esp + 0x14]
  mov esi, eax
  shl esi, 3
  sub esi, eax
  add esi, %(sur)s
  mov ecx, 7
cm_cp_given:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  test al, al
  je cm_cp_given_end
  inc esi
  inc edi
  dec ecx
  jne cm_cp_given
cm_cp_given_end:
  mov byte ptr [edi], 0
  mov dword ptr [esp + 0x28], edi
  mov ecx, dword ptr [esp + 0x10]
  call %(age)s
  movzx eax, ax
  cmp eax, %(age_mask)s
  jbe cm_age_ok
  mov eax, %(age_mask)s
cm_age_ok:
  mov esi, %(dec100)s
  add esi, eax
  add esi, eax
  mov edi, dword ptr [esp + 0x28]
  mov al, byte ptr [esi]
  mov byte ptr [edi], 0x20
  mov byte ptr [edi + 1], al
  mov al, byte ptr [esi + 1]
  mov byte ptr [edi + 2], al
  mov esi, %(str_age_suffix)s
  mov ax, word ptr [esi]
  mov word ptr [edi + 3], ax
  mov byte ptr [edi + 5], 0
  inc dword ptr [esp + 0x0C]
cm_count:
  inc dword ptr [esp + 0x30]
  jmp cm_scan
cm_scan_end:
  mov eax, dword ptr [esp + 0x0C]
  test eax, eax
  jne cm_have_rows
  # Nothing scanned at all: this used to return silently, so the player just saw "clicking
  #   does nothing" and could not tell "no child here" from "a gate refused". Paging past the
  #   end (start > 0) stays silent; an empty FIRST page gets an explicit notice.
  cmp dword ptr [esp + 0x2C], 0
  jne cm_exit
  push 0
  push 0
  push 4
  push %(str_none)s
  push 1
  call %(dialog)s
  add esp, 0x14
  jmp cm_exit
cm_have_rows:
  add eax, dword ptr [esp + 0x2C]
  cmp dword ptr [esp + 0x30], eax
  jbe cm_nav_prev
  mov eax, dword ptr [esp + 0x0C]
  mov dword ptr [eax * 4 + %(sub_ptr)s], %(str_next)s
  mov word ptr [eax * 2 + %(slot_arr)s], 0xFFFE
  inc dword ptr [esp + 0x0C]
cm_nav_prev:
  cmp dword ptr [esp + 0x2C], 0
  je cm_show
  mov eax, dword ptr [esp + 0x0C]
  mov dword ptr [eax * 4 + %(sub_ptr)s], %(str_prev)s
  mov word ptr [eax * 2 + %(slot_arr)s], 0xFFFD
  inc dword ptr [esp + 0x0C]
cm_show:
  mov eax, dword ptr [esp + 0x0C]
  mov dword ptr [%(c_rows)s], eax
  mov ecx, %(sub_ptr)s
  push 0
  push 0
  push 4
  push ecx
  push eax
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je cm_exit
  movzx eax, ax
  movzx edx, word ptr [eax * 2 + %(slot_arr)s]
  cmp edx, 0xFFFE
  jne cm_not_next
  inc dword ptr [%(c_nav)s]
  add dword ptr [esp + 0x2C], %(page_max)s
  jmp cm_page
cm_not_next:
  cmp edx, 0xFFFD
  jne cm_kid
  inc dword ptr [%(c_nav)s]
  sub dword ptr [esp + 0x2C], %(page_max)s
  jmp cm_page
cm_kid:
  mov dword ptr [esp + 0x14], edx
  lea ecx, [edx + edx * 2]
  shl ecx, 4
  sub ecx, edx
  add ecx, %(pool)s
  mov dword ptr [esp + 0x10], ecx
  push 0
  push 0
  push 4
  push %(act_ptr)s
  push %(act_n)s
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je cm_exit
  movzx eax, ax
  cmp ax, %(act_last)s
  jae cm_exit
  mov dword ptr [esp + 0x18], eax
  push 0
  push 0
  push 4
  push %(teach_ptr)s
  push %(teach_n)s
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je cm_exit
  movzx eax, ax
  cmp ax, %(teach_last)s
  jae cm_exit
  mov dword ptr [esp + 0x1C], eax
  push 0
  push 0
  push 4
  push %(tier_ptr)s
  push %(tier_n)s
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je cm_exit
  movzx eax, ax
  cmp ax, %(tier_last)s
  jae cm_exit
  mov dword ptr [esp + 0x20], eax
  # ---- M3c-2 kid detail panel: args -> static area, then call (pushad/popad safe) ----
  mov ecx, dword ptr [esp + 0x10]
  mov dword ptr [%(kd_ent)s], ecx
  mov ecx, dword ptr [esp + 0x14]
  mov dword ptr [%(kd_slot)s], ecx
  mov ecx, dword ptr [esp + 0x18]
  mov dword ptr [%(kd_act)s], ecx
  mov ecx, dword ptr [esp + 0x1C]
  mov dword ptr [%(kd_teach)s], ecx
  mov ecx, dword ptr [esp + 0x20]
  mov dword ptr [%(kd_tier)s], ecx
  call %(kd_show)s
  # ====== M5: one per month + gold cost + advance days ======
  # gate 1: already raised this month? ym = (year << 8 | month) + 1; 0 means never
  movzx eax, byte ptr [%(date_y)s]
  shl eax, 0x8
  movzx ecx, byte ptr [%(date_m)s]
  or eax, ecx
  inc eax
  mov ecx, dword ptr [%(f_ym)s]
  cmp eax, ecx
  je cm_g1
  mov dword ptr [%(f_ym)s], eax
  mov dword ptr [%(f_cnt)s], 0
cm_g1:
  cmp dword ptr [%(f_cnt)s], %(mcap)s
  jae cm_deny_month
  # gate 2: days = ACT_DAYS[act]; need DATE_D + days <= 0x1e (0x1f rolls month -> month hook)
  mov ecx, dword ptr [%(kd_act)s]
  movzx edx, byte ptr [ecx + %(act_days)s]
  mov dword ptr [%(f_days)s], edx
  movzx eax, byte ptr [%(date_d)s]
  add eax, edx
  cmp eax, %(day_max)s
  ja cm_deny_time
  # gate 3: gold = days * GOLD_PER_DAY (pay uses sat_sub, no balance check -> compare first)
  imul edx, edx, %(gold_per_day)s
  mov dword ptr [%(f_gold)s], edx
  movzx eax, word ptr [%(gold_ptr)s]
  cmp eax, edx
  jb cm_deny_gold
  # confirm dialog: 3 rows -- [0] cost line (days/gold for this activity),
  #   [1] "go ahead", [2] "think again".  Only picking row 1 really commits;
  #   row 0 (the cost line), row 2 and cancel (0xffff) all mean "give up".
  #   The pointer array is assembled here into a 3-slot scratch in the FOSTER area.
  mov ecx, dword ptr [%(kd_act)s]
  imul eax, ecx, %(ms_row)s
  add eax, %(cost0)s
  mov dword ptr [%(cost_arr)s], eax
  mov dword ptr [%(cost_arr)s + 4], %(ok_str)s
  mov dword ptr [%(cost_arr)s + 8], %(cancel_str)s
  push 0
  push 0
  push 4
  push %(cost_arr)s
  push 3
  call %(dialog)s
  add esp, 0x14
  cmp ax, 1
  jne cm_exit
  # pay
  push dword ptr [%(f_gold)s]
  call %(pay)s
  add esp, 4
  # ---- M5b: book this month + show the child's line NOW, before the clock moves ----
  #   Order matters to the player: 0x4A0D50 fires the game's own daily events, so when the
  #   day advance came first the user saw a daimyo's messenger dialog and only THEN the
  #   child's line. Speak first, then let time pass.
  inc dword ptr [%(f_cnt)s]
  mov eax, dword ptr [%(kd_act)s]
  mov dword ptr [%(msg_act)s], eax
  mov eax, dword ptr [%(kd_slot)s]
  mov dword ptr [%(msg_slot)s], eax
  call %(kd_msg)s
  # advance days: 0x4A0D50 is **cdecl** -- the caller must pop the 2 args;
  #   (native sites all do `push 1; push 0x18; call 0x4A0D50; add esp,8`).
  #   Forgetting the add esp,8 here made `pop ecx` reload the stray arg 0x18
  #   every pass => the loop never ended and the date ran away forever.
  mov ecx, dword ptr [%(f_days)s]
  test ecx, ecx
  je cm_day_done                     # never enter the loop with 0 days (dec would wrap to 4G)
cm_day_l:
  push ecx                           # the callee does not preserve ecx
  push 1
  push %(adv_hours)s
  call %(adv_day)s
  add esp, 0x8
  pop ecx
  dec ecx
  jne cm_day_l
cm_day_done:
  mov eax, dword ptr [%(ring_tail)s]
  and eax, 0x3F
  shl eax, 3
  add eax, %(ring_ents)s
  movzx ecx, word ptr [esp + 0x14]
  mov word ptr [eax], cx
  mov ecx, dword ptr [esp + 0x18]
  mov byte ptr [eax + 1], cl
  mov ecx, dword ptr [esp + 0x1C]
  mov byte ptr [eax + 2], cl
  mov ecx, dword ptr [esp + 0x20]
  mov byte ptr [eax + 3], cl
  mov word ptr [eax + 4], 0
  mov word ptr [eax + 6], 0
  mov ecx, dword ptr [%(ring_tail)s]
  inc ecx
  mov dword ptr [%(ring_tail)s], ecx
  inc dword ptr [%(c_push)s]
  movzx ecx, word ptr [esp + 0x14]
  mov dword ptr [%(last_slot)s], ecx
  mov ecx, dword ptr [esp + 0x18]
  mov dword ptr [%(last_act)s], ecx
  jmp cm_exit
  # ---- M5 deny: single button notice box (same 0x47BED0 convention) ----
cm_deny_month:
  push 0
  push 0
  push 4
  push %(deny_month_ptr)s
  push 1
  call %(dialog)s
  add esp, 0x14
  jmp cm_exit
cm_deny_time:
  push 0
  push 0
  push 4
  push %(deny_time_ptr)s
  push 1
  call %(dialog)s
  add esp, 0x14
  jmp cm_exit
cm_deny_gold:
  push 0
  push 0
  push 4
  push %(deny_gold_ptr)s
  push 1
  call %(dialog)s
  add esp, 0x14
cm_exit:
  add esp, 0x38
  pop edi
  pop esi
  pop ebp
  pop ebx
  jmp %(menu_top)s
"""


def lint_src(src):
    """keystone 陷阱: 源里裸写的多位十进制立即数会按十六进制吃进去 => 一律 0x 前缀。
    另外 keystore 源必须 ASCII (中文注释会 UnicodeEncodeError)。"""
    import re
    bad = [(m.group(0), src[:m.start()].count('\n') + 1)
           for m in re.finditer(r'(?<![0-9a-fA-Fx,.])\d{2,}(?![0-9a-fA-F])', src)]
    assert not bad, 'SRC 有未加 0x 的立即数(会被当十六进制): %s' % bad[:8]
    nonascii = [c for c in src if ord(c) > 0x7F]
    assert not nonascii, 'SRC 含非 ASCII 字符(keystone 会炸): %r' % nonascii[:8]


def _hexsubs(L):
    """L 的值给成 0x 字符串 (int 直接 %s 会变成十进制, 十进制又会被 keystone 当十六进制吃)"""
    return {k: ('0x%X' % v if isinstance(v, int) else v) for k, v in L.items()}


def build_hook(hook_va, L):
    """A) 回家菜单钩子。L 需含 menu_ptr/menu_code/str_va/s_*/c_menu/birth_label/pick。返回 (code, ins)。"""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_OPT_SYNTAX_INTEL
    subs = _hexsubs(L)
    subs['dialog'] = '0x%X' % DIALOG
    subs['str_foster'] = '0x%X' % (L['str_va'] + S_HOME * STR_ROW)
    subs['str_birth'] = '0x%X' % L['birth_label']
    src = SRC_HOOK % subs
    lint_src(src)
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    ks.syntax = KS_OPT_SYNTAX_INTEL
    code = bytes(ks.asm(src, hook_va)[0])
    return code, src


def build_foster(foster_va, L):
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_OPT_SYNTAX_INTEL
    subs = _hexsubs(L)
    subs['ring_tail'] = '0x%X' % (L['ring'] + CG.RING_TAIL_OFF)
    subs['ring_ents'] = '0x%X' % (L['ring'] + CG.RING_ENTS_OFF)
    subs.update({'dialog': '0x%X' % DIALOG, 'age': '0x%X' % AGE_GET,
                 'menu_top': '0x%X' % MENU_TOP,
                 'cap': '0x%X' % L['cap'],
                 'page_max': '0x%X' % PAGE_KIDS,
                 'str_next': '0x%X' % (L['str_va'] + S_NEXT * STR_ROW),
                 'str_prev': '0x%X' % (L['str_va'] + S_PREV * STR_ROW),
                 'age_mask': '0x%X' % AGE_GET_MASK,
                 'str_age_suffix': '0x%X' % (L['str_va'] + S_AGE_SUFFIX * STR_ROW),
                 # 活动/教席/档次子菜单: 项数 = 表长 + 1(暂不培养); 选中"暂不培养"的下标 = 表长
                 'act_n': '0x%X' % (len(CG.ACTS) + 1), 'act_last': '0x%X' % len(CG.ACTS),
                 'teach_n': '0x%X' % (len(CG.TEACHERS) + 1), 'teach_last': '0x%X' % len(CG.TEACHERS),
                 'tier_n': '0x%X' % (len(TIER_NAMES) + 1), 'tier_last': '0x%X' % len(TIER_NAMES),
                 # M3c-2 培养详情面板: 参数静态区 + 入口 (面板自己 pushad/popad)
                 'kd_ent': '0x%X' % L['kd_ent'], 'kd_slot': '0x%X' % L['kd_slot'],
                 'kd_act': '0x%X' % L['kd_act'], 'kd_teach': '0x%X' % L['kd_teach'],
                 'kd_tier': '0x%X' % L['kd_tier'], 'kd_show': '0x%X' % L['kd_show'],
                 # ---- M5: 节奏/花费 ----
                 # M5b: 菜单打开时复跑一遍孩子预载桩, 把孩子「所在城」同步成父亲当前城
                 'child_pass': '0x%X' % L['child_pass'],
                 'date_y': '0x%X' % CG.DATE_Y, 'date_m': '0x%X' % CG.DATE_M,
                 'date_d': '0x%X' % CG.DATE_D,
                 'f_ym': '0x%X' % L['f_ym'], 'f_cnt': '0x%X' % L['f_cnt'],
                 'f_days': '0x%X' % L['f_days'], 'f_gold': '0x%X' % L['f_gold'],
                 'msg_act': '0x%X' % L['msg_act'], 'msg_slot': '0x%X' % L['msg_slot'],
                 'act_days': '0x%X' % L['act_days'],
                 'mcap': '0x%X' % CG.MONTHLY_CAP, 'day_max': '0x%X' % CG.DAY_MAX,
                 'gold_per_day': '0x%X' % CG.GOLD_PER_DAY, 'gold_ptr': '0x%X' % CG.GOLD_PTR,
                 'pay': '0x%X' % CG.PAY, 'adv_day': '0x%X' % CG.ADVANCE_DAY,
                 'adv_hours': '0x%X' % CG.ADVANCE_HOURS,
                 # 费用提示: cost0 = 池首 + MS_COST0*行宽, 行地址 = cost0 + act*行宽
                 #          三行指针数组落 FOSTER 区尾部的 12B 暂存 (运行时拼)
                 'ms_row': '0x%X' % MS_STR_ROW,
                 'cost0': '0x%X' % (L['msg_str'] + MS_COST0 * MS_STR_ROW),
                 'cost_arr': '0x%X' % L['cost_arr'],
                 'ok_str': '0x%X' % (L['msg_str'] + MS_OK * MS_STR_ROW),
                 'cancel_str': '0x%X' % (L['msg_str'] + MS_CANCEL * MS_STR_ROW),
                 'confirm_ptr': '0x%X' % L['confirm_ptr'],
                 # 一个孩子都没扫到时的明说 (静默 return 会让"点了没反应"无法诊断)
                 'str_none': '0x%X' % (L['msg_str'] + MS_NONE * MS_STR_ROW),
                 'deny_month_ptr': '0x%X' % L['deny_month_ptr'],
                 'deny_time_ptr': '0x%X' % L['deny_time_ptr'],
                 'deny_gold_ptr': '0x%X' % L['deny_gold_ptr'],
                 'kd_msg': '0x%X' % L['kd_msg']})
    src = SRC_FOSTER % subs
    lint_src(src)
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    ks.syntax = KS_OPT_SYNTAX_INTEL
    code = bytes(ks.asm(src, foster_va)[0])
    return code, src


def build_birth(birth_va, L):
    """C) 生孩子处理程序 (码 7 的第二条路, 由 cm_foster 头部按 BIRTH_PICK 分流)。

    L 需含 c_birth/menu_top/name_pool/avail/avail_n/used/sub_ptr/slot_arr/child_bm/pool/cap/
    flagtab/sched/sched_end/child_pass/date_y/giv/sur/msg_str/str_va/slot_lo/name_tmp/msg_arr。
    返回 (code, src)。"""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_OPT_SYNTAX_INTEL
    subs = _hexsubs(L)
    subs['menu_top'] = '0x%X' % MENU_TOP
    subs['dialog'] = '0x%X' % DIALOG
    subs['page_max'] = '0x%X' % BIRTH_NAME_PAGE
    subs['offer'] = '0x%X' % BIRTH_NAME_OFFER
    subs['count'] = '0x%X' % BIRTH_NAME_COUNT
    subs['rand'] = '0x%X' % CG.RAND
    subs['str_next'] = '0x%X' % (L['str_va'] + S_NEXT * STR_ROW)
    subs['str_prev'] = '0x%X' % (L['str_va'] + S_PREV * STR_ROW)
    subs['slot_lo'] = '0x%X' % L['slot_lo']
    subs['oid_hi'] = '0x%X' % (BIRTH_OID_MAX - 1)
    subs['str_none'] = '0x%X' % (L['msg_str'] + MS_NO_SLOT * MS_STR_ROW)
    # 出生提示: 标题/住在哪两行是静态串, 姓名行是运行时拼进 name_tmp 的连续串
    subs['born_str'] = '0x%X' % (L['msg_str'] + MS_BORN * MS_STR_ROW)
    subs['born_at'] = '0x%X' % (L['msg_str'] + MS_BORN_AT * MS_STR_ROW)
    subs['born_gk'] = '0x%X' % (L['msg_str'] + MS_BORN_GK * MS_STR_ROW)
    subs['name_tmp'] = '0x%X' % L['name_tmp']
    subs['msg_arr'] = '0x%X' % L['msg_arr']
    src = SRC_BIRTH % subs
    lint_src(src)
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    ks.syntax = KS_OPT_SYNTAX_INTEL
    code = bytes(ks.asm(src, birth_va)[0])
    return code, src


def jmp_rel(site, target):
    """5 字节 E9 rel32 补丁 (构建与验收同一算法, 防止两边算歪)"""
    import struct
    return b'\xE9' + struct.pack('<i', target - (site + 5))


# ================= 回读自检 =================
def _dis(code, origin):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    ins = list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, origin))
    assert ins and sum(len(i.bytes) for i in ins) == len(code), '反汇编未覆盖全部字节'
    return ins


def _mk(ins):
    def one(mn, *pats):
        got = [i for i in ins if i.mnemonic == mn and all(p in i.op_str for p in pats)]
        assert len(got) == 1, ('应恰 1 条: %s %s (命中 %d)' % (mn, pats, len(got)))
        return got[0]

    def cnt(mn, *pats):
        return len([i for i in ins if i.mnemonic == mn and all(p in i.op_str for p in pats)])

    def cntx(mn, exact):
        return len([i for i in ins if i.mnemonic == mn and i.op_str == exact])
    return one, cnt, cntx


def selfcheck_hook(code, origin, L):
    ins = _dis(code, origin)
    one, cnt, cntx = _mk(ins)
    dl = '0x%x' % DIALOG
    one('call', dl)
    # 0x47BED0 实机约定: arg1 = 条目数 / arg2 = 串指针数组 / arg3 = 样式 (见 0x47BED0 入口
    #   mov edx,[esp+4] + test dx,dx + cmp ax,dx)。末推 = arg1, 必须是 ecx(=cnt+1);
    #   把 s_flag(样式) 推在末位会让菜单只画 2 项且样式参数错 (2026-10-06 实机卡死根因)。
    _ci = [i for i in ins if i.mnemonic == 'call' and i.op_str == dl][0]
    _j = ins.index(_ci)
    _pre = [(x.mnemonic, x.op_str) for x in ins[_j - 3:_j]]
    assert _pre == [('push', 'dword ptr [0x%x]' % L['s_flag']), ('push', 'edx'), ('push', 'ecx')], \
        '对话框实参顺序必须是 (样式, 指针数组, 条目数): 末推=arg1=条目数, 现在是 %s' % (_pre,)
    assert cnt('add', 'esp, 0x14') == 1, '只调一次对话框'
    one('cmp', 'ax, -1')
    assert cnt('cmp', 'cx, word ptr [0x%x]' % L['s_cnt']) == 2, '两次检查: item 7 和 item 8'
    # ★ 两次比较的"偏"必须相反: 第一次比 ax==cnt (培养孩子), 第二次比 ax-1==cnt (生孩子)。
    #   以前写成"先 inc 再比 cnt", 于是点第 cnt+2 行(生孩子)时两条都不中, 掉去查没拷过的
    #   码表空位 = 0 = 休息 (2026-10-07 实机症状); 反过来点最后一个原生项会误进生孩子。
    _cc = [i for i in ins if i.mnemonic == 'cmp' and i.op_str == 'cx, word ptr [0x%x]' % L['s_cnt']]
    _i1, _i2 = ins.index(_cc[0]), ins.index(_cc[1])
    assert ins[_i1 + 1].mnemonic == 'je' and ins[_i2 + 1].mnemonic == 'je'
    assert ins[_i2 - 1].mnemonic == 'dec' and ins[_i2 + 2].mnemonic == 'inc', \
        '第二次比较前要 dec ecx(比 ax-1==cnt), 比较后要 inc 回原序号'
    one('movzx', 'eax, word ptr [ecx*2 + 0x%x]' % L['menu_code'])   # 序号 -> 原生指令码
    # 两个新项都发**码 7** (跳转表只有 0x4CD47C 这一个空槽), 谁被选中记在 BIRTH_PICK。
    #   生孩子绝不能再发"码 8 + jmp 处理程序": 钩子还站在构建器的帧上(0x34 字节没拆),
    #   从那儿 jmp 过去就是把调用方的 esp 和栈上返回地址一起弄歪 (2026-10-07 实机=点生孩子变休息)。
    assert cnt('mov', 'eax, 7') == 2, '培养孩子/生孩子 同发码 7'
    one('mov', 'dword ptr [0x%x], 0' % L['pick'])
    one('mov', 'dword ptr [0x%x], 1' % L['pick'])
    one('mov', 'eax, 0xffffffff')   # capstone 把 -1 打成 0xffffffff
    one('inc', 'dword ptr [0x%x]' % L['c_menu'])
    assert cnt('dec', 'ecx') == 2, '码表 + 指针数组两份拷贝循环'
    one('mov', 'dword ptr [edx + eax], 0x%x' % (L['str_va'] + S_HOME * STR_ROW))  # 尾追"培养孩子"
    one('mov', 'dword ptr [edx + eax + 4], 0x%x' % L['birth_label'])  # 尾追"生孩子"(独立标签行)
    # 收尾必须与原生 0x4CD581..0x4CD58C 同构 (pop edi/esi/ebp + add esp,0x24 + ret), 且不能碰原生翻译那条
    tail = ins[-5:]
    assert [i.mnemonic for i in tail] == ['pop', 'pop', 'pop', 'add', 'ret'], [i.mnemonic for i in tail]
    assert [i.op_str for i in tail[:3]] == ['edi', 'esi', 'ebp'], [i.op_str for i in tail[:3]]
    assert tail[3].op_str == 'esp, 0x24'
    assert cnt('ret') == 1 and cnt('mov', 'ax, word ptr [esp + eax*2 + 4]') == 0, '不得复用原生序号翻译'
    for k in ('s_ebx', 's_flag', 's_cnt', 's_ptrs', 's_cnt1'):
        assert cnt('mov', 'dword ptr [0x%x]' % L[k]) >= 1, k
    one('mov', 'ebx, dword ptr [0x%x]' % L['s_ebx'])
    return ins


def selfcheck_foster(code, origin, L):
    ins = _dis(code, origin)
    one, cnt, cntx = _mk(ins)
    dl = '0x%x' % DIALOG
    # 4 次选项 + 1 次确认 + 3 次门禁拒绝 + 1 次「此城没有可培养的孩子」 = 9 次原生对话框 (M5/M5b)
    assert cnt('call', dl) == 9, '四次选项 + 确认 + 三个拒绝 + 空名单 = 9 次原生对话框 (命中 %d)' % cnt('call', dl)
    assert cnt('add', 'esp, 0x14') == 9
    assert cntx('push', '4') == 9, '选项子菜单一律 flag=4 (实测 0x445758/0x412E64)'
    assert cntx('push', '0') == 18, '每次两枚 0 尾参'
    one('call', '0x%x' % AGE_GET)
    assert cnt('sub', 'esp, 0x38') == 1 and cnt('add', 'esp, 0x38') == 1
    # 入口 = 分流器 (码 7 一个槽, 两条路): cmp [pick],0 / je 本体 / jmp 生孩子, 然后才是本体的 4 连 push
    assert [i.mnemonic for i in ins[:3]] == ['cmp', 'je', 'jmp'], [i.mnemonic for i in ins[:3]]
    assert ins[0].op_str == 'dword ptr [0x%x], 0' % L['pick'], ins[0].op_str
    assert ins[2].op_str == '0x%x' % L['birth_handler'], ins[2].op_str
    head = ins[3:7]
    assert [i.op_str for i in head] == ['ebx', 'ebp', 'esi', 'edi'], [i.op_str for i in head]
    tail = ins[-6:]
    assert [i.mnemonic for i in tail] == ['add', 'pop', 'pop', 'pop', 'pop', 'jmp'], [i.mnemonic for i in tail]
    assert [i.op_str for i in tail[1:5]] == ['edi', 'esi', 'ebp', 'ebx']
    assert tail[5].op_str == '0x%x' % MENU_TOP, '完事回菜单头'
    assert cnt('jmp', '0x%x' % MENU_EXIT) == 0, '不直接退出回家菜单'
    # 扫描门: 位图 / 儿童态 nibble / 在场位 / 同城 / 每页上限
    one('bt', 'edx, ecx')
    one('movzx', 'edx, byte ptr [ecx + 0x%x]' % L['bm'])
    one('cmp', 'dl, 0xb')
    one('test', 'byte ptr [ecx + 0x2d], 0x80')
    one('cmp', 'dx, word ptr [esp + 4]')
    one('cmp', 'dword ptr [esp + 0xc], %s' % cap_imm(PAGE_KIDS))
    one('inc', 'dword ptr [0x%x]' % L['c_notcity'])
    one('inc', 'dword ptr [0x%x]' % L['c_panel'])
    one('inc', 'dword ptr [0x%x]' % L['c_push'])
    one('mov', 'dword ptr [0x%x]' % L['last_slot'])
    one('mov', 'dword ptr [0x%x]' % L['last_act'])
    # 姓名拼装: 两段 7B 上限拷贝 + " NN岁"
    assert cnt('mov', 'ecx, 7') == 2, '姓/名各一条有界拷贝'
    assert cnt('dec', 'ecx') == 3, '两条名字拷贝 + M5 推天数循环'
    one('mov', 'byte ptr [edi], 0x20')
    one('mov', 'esi, 0x%x' % L['dec100'])
    one('mov', 'eax, 0x63')
    assert cnt('add', 'esi, eax') == 2, 'DEC100 + age*2'
    # 指令入队 (分工: UI 只写 tail, head 归成长桩)
    one('and', 'eax, 0x3f')
    one('mov', 'word ptr [eax], cx')
    one('mov', 'word ptr [eax + 4], 0')
    one('mov', 'word ptr [eax + 6], 0')
    _ld = one('mov', 'ecx, dword ptr [0x%x]' % (L['ring'] + 4))   # tail 读-改-写 (UI 只碰 tail)
    _i = ins.index(_ld)
    assert [_x.mnemonic for _x in ins[_i + 1:_i + 3]] == ['inc', 'mov'], ins[_i + 1:_i + 3]
    assert ins[_i + 2].op_str == 'dword ptr [0x%x], ecx' % (L['ring'] + 4)
    assert cnt('mov', 'dword ptr [0x%x]' % L['ring']) == 0, 'UI 不得写 head'
    # 三级子菜单的"暂不培养"下标 = 各表长
    for n in (len(CG.ACTS), len(CG.TEACHERS), len(TIER_NAMES)):
        one('cmp', 'ax, %s' % (('%d' % n) if n < 10 else ('0x%x' % n)))   # capstone: <10 打十进制
    # 分页导航: 哨兵写进行表 + 靠哨兵(不是行号)分派 => "只有上一页/只有下一页"也不会走歪
    sa = 'word ptr [eax*2 + 0x%x]' % L['slot_arr']
    one('mov', sa, '0xfffe')
    one('mov', sa, '0xfffd')
    one('movzx', 'edx, ' + sa)
    one('cmp', 'edx, 0xfffe')
    one('cmp', 'edx, 0xfffd')
    one('add', 'dword ptr [esp + 0x2c], %s' % cap_imm(PAGE_KIDS))
    one('sub', 'dword ptr [esp + 0x2c], %s' % cap_imm(PAGE_KIDS))
    # 两个导航分支都跳回"重开一页"(cm_page: 把行表/计数清零的那条), 且只跳这两次
    pg = [i for i in ins if i.mnemonic == 'mov' and i.op_str == 'dword ptr [esp + 8], 0']
    assert len(pg) == 1, 'cm_page 复位点应唯一 (命中 %d)' % len(pg)
    assert cnt('jmp', '0x%x' % pg[0].address) == 2, '下一页/上一页各回一次页首'
    for mn in ('add', 'sub'):
        k = [j for j, i in enumerate(ins) if i.mnemonic == mn and 'esp + 0x2c], ' + cap_imm(PAGE_KIDS) in i.op_str][0]
        assert ins[k + 1].mnemonic == 'jmp' and ins[k + 1].op_str == '0x%x' % pg[0].address
    assert cnt('mov', 'dword ptr [esp + 0x34]') == 0, '导航不写行号 (行号在单侧导航时会撞车)'
    # M3c-2: 选完四级的参数落静态区 + call 详情面板 (写参必须在 call 之前, 且一次)
    one('call', '0x%x' % L['kd_show'])
    for nm, k in (('ent', 'kd_ent'), ('slot', 'kd_slot'), ('act', 'kd_act'),
                  ('teach', 'kd_teach'), ('tier', 'kd_tier')):
        # ★ 模式里必须带 ", ecx": M5 之后的反馈小框参数搬运也读同一批地址
        #   (`mov eax, dword ptr [kd_slot]`), 只用 "dword ptr [addr]" 会命中两条。
        st = one('mov', 'dword ptr [0x%x], ecx' % L[k])
        assert st.op_str == 'dword ptr [0x%x], ecx' % L[k], (nm, st.op_str)
    _kc = ins.index(one('call', '0x%x' % L['kd_show']))
    for k in ('kd_ent', 'kd_slot', 'kd_act', 'kd_teach', 'kd_tier'):
        assert any(i.op_str == 'dword ptr [0x%x], ecx' % L[k] for i in ins[:_kc]), \
            '面板参数 %s 必须在 call 之前写好' % k
    # 分页扫到的"槽"必须是真槽: 游标在 cm_scan 里已 inc, 取回要 dec。
    # ★ 这里踩过坑: cm_same 开头一句 `mov eax,[esp+0x30]`(累计匹配数)把 eax 冲掉了,
    #   于是 slot_arr 存的是"第几个匹配"而不是槽 => 姓名表按它取会取到别人的名字,
    #   选中的实体也算错。现在在写 [esp+0x14] 之前补 `mov eax,[esp+8]; dec eax` 取回真槽。
    assert cnt('mov', 'eax, dword ptr [esp + 8]') == 2, '扫描头一处 + 取回真槽一处'
    assert cnt('dec', 'eax') == 1, '取回真槽的 dec'
    # 分页埋点: 翻页计数在两条分支各一次; 行数读数落在弹窗口令之前 (取最大值, 不是求和)
    assert cnt('inc', 'dword ptr [0x%x]' % L['c_nav']) == 2, '下一页/上一页各计一次 PAGE_NAV'
    _rw = one('mov', 'dword ptr [0x%x], eax' % L['c_rows'])
    assert ins[ins.index(_rw) + 1].op_str == 'ecx, 0x%x' % L['sub_ptr'], 'PAGE_ROWS 必须写在 push 行数之前'
    # ---- M5: 每月 1 次门 / 天数门 / 金门 / 扣金 / 推天数 / 反馈 ----
    # ym = (年<<8|月)+1: 换月才把计数归零, 0 专门留给"本进程从未培养"
    one('shl', 'eax, 8')
    one('or', 'eax, ecx')
    one('inc', 'eax')
    one('mov', 'ecx, dword ptr [0x%x]' % L['f_ym'])
    one('mov', 'dword ptr [0x%x], 0' % L['f_cnt'])
    one('cmp', 'dword ptr [0x%x], 1' % L['f_cnt'])
    one('movzx', 'edx, byte ptr [ecx + 0x%x]' % L['act_days'])
    one('mov', 'dword ptr [0x%x], edx' % L['f_days'])
    one('movzx', 'eax, byte ptr [0x5205f2]')
    one('imul', 'edx, edx, %d' % CG.GOLD_PER_DAY)
    one('mov', 'dword ptr [0x%x], edx' % L['f_gold'])
    one('movzx', 'eax, word ptr [0x%x]' % CG.GOLD_PTR)
    one('add', 'eax, edx')
    one('call', '0x%x' % CG.PAY)
    one('call', '0x%x' % CG.ADVANCE_DAY)
    one('call', '0x%x' % L['kd_msg'])
    # ★★ M5b 事故 (2026-10-07 实机): "每次进城回家, 点培养孩子就不行了, 非要等下一个月"。
    #   根因: 名单按「孩子所在城 == 主角所在城」筛, 而孩子的城只在 child_pass 里随父亲
    #   同步 (make_child / 月钩 rearm) => 主角一移动, 孩子还挂在上一个城, 名单空到下次月钩。
    #   child_pass 自包含且幂等 (自己 push/pop ebx/esi/edi/ebp, 无实参), 所以在扫名单前补跑一次。
    _cp = one('call', '0x%x' % L['child_pass'])
    assert ins.index(_cp) < ins.index(one('call', '0x%x' % L['kd_show'])), \
        'child_pass 必须在扫名单/弹菜单之前跑 (它负责把孩子搬到父亲当前城)'
    # ★★ M5b 顺序: 反馈框必须在推天数之前 —— 0x4A0D50 会触发原生每日事件 (使者/访问),
    #   原来是"先推天数再弹台词", 玩家看到的是"大名的对话后, 孩子才出现"。
    assert ins.index(one('call', '0x%x' % L['kd_msg'])) \
        < ins.index(one('call', '0x%x' % CG.ADVANCE_DAY)), \
        '孩子台词必须在日期推进之前弹出 (否则会被原生每日事件的对话挤到后面)'
    assert cntx('push', '1') == 5, '推天数 1 + 三个拒绝框 + 空名单 1 (命中 %d)' % cntx('push', '1')
    assert cnt('inc', 'dword ptr [0x%x]' % L['f_cnt']) == 1, '只在这一个月+1 处落账'
    _g0 = cntx('test', 'ecx, ecx')
    assert _g0 == 1, '天数 0 的守卫应恰 1 处 (命中 %d)' % _g0
    # ★★ 0x4A0D50 是 cdecl: 调用方必须紧跟 add esp,8 清两枚实参。
    #    漏掉它 => `pop ecx` 每次捡回残留实参 0x18, 循环永不结束, 日期一路狂奔 (2026-10-07 实机症状)。
    _adv = ins.index(one('call', '0x%x' % CG.ADVANCE_DAY))
    assert ins[_adv + 1].mnemonic == 'add' and ins[_adv + 1].op_str == 'esp, 8', \
        '推天数必须紧跟 add esp,8 (实得 %s %s)' % (ins[_adv + 1].mnemonic, ins[_adv + 1].op_str)
    assert cntx('add', 'esp, 8') == 1, '只这一处 cdecl 调用'
    _pp = ins.index(one('pop', 'ecx'))
    assert _adv < _pp, '先清参数再 pop 计数'
    # 费用提示: [cost0 + act*行宽] 落三槽指针数组 -> 3 项确认框, 只有 ax==1 才真办
    _rw24 = ('%d' % MS_STR_ROW) if MS_STR_ROW < 10 else ('0x%x' % MS_STR_ROW)
    one('imul', 'eax, ecx, %s' % _rw24)
    one('add', 'eax, 0x%x' % (L['msg_str'] + MS_COST0 * MS_STR_ROW))
    # ★ keystone 会把 [base + 4] 折进绝对地址 => 回读是三条相邻地址, `[0x... + 4]` 这种写法对不上
    one('mov', 'dword ptr [0x%x], eax' % L['cost_arr'])
    one('mov', 'dword ptr [0x%x], 0x%x' % (L['cost_arr'] + 4,
                                           L['msg_str'] + MS_OK * MS_STR_ROW))
    one('mov', 'dword ptr [0x%x], 0x%x' % (L['cost_arr'] + 8,
                                           L['msg_str'] + MS_CANCEL * MS_STR_ROW))
    assert cntx('push', '3') == 1, '确认框是 3 项 (费用行 + 就这么办 + 再想想)'
    one('cmp', 'ax, 1')
    assert ins[ins.index(one('cmp', 'ax, 1')) + 1].mnemonic == 'jne', '只有选 1 才继续'
    # 反馈: 活动码/槽号先落静态区, 再 call kd_msg (面板与反馈框共用静态区约定)
    one('mov', 'dword ptr [0x%x], eax' % L['msg_act'])
    for k in ('f_ym', 'f_cnt', 'f_days', 'f_gold', 'msg_act', 'msg_slot'):
        assert L[k] > 0, k
    return ins


def selfcheck_birth(code, origin, L):
    """生孩子处理程序自检 (码 7 的第二条路; 实例化交回已验证的 child_pass)。"""
    ins = _dis(code, origin)
    one, cnt, cntx = _mk(ins)
    dl = '0x%x' % DIALOG
    pm = cap_imm(BIRTH_NAME_PAGE)
    # 帧: push ebx/ebp/esi/edi + sub esp,0x20 ... add esp,0x20 + pop edi/esi/ebp/ebx + jmp 菜单头
    head = ins[:4]
    assert [i.op_str for i in head] == ['ebx', 'ebp', 'esi', 'edi'], [i.op_str for i in head]
    one('sub', 'esp, 0x20')
    one('add', 'esp, 0x20')
    # 收尾不在 ins 末尾: v2 之后还接了 bn_avail/bn_live 两个子程序 (各自 ret 收尾),
    #   所以按"最后一条 jmp 菜单头"定位 b_cancel 那五行。
    _tj = [k for k, i in enumerate(ins)
           if i.mnemonic == 'jmp' and i.op_str == '0x%x' % MENU_TOP][-1]
    tail = ins[_tj - 4:_tj + 1]
    assert [i.mnemonic for i in tail] == ['pop', 'pop', 'pop', 'pop', 'jmp'], [i.mnemonic for i in tail]
    assert [i.op_str for i in tail[:4]] == ['edi', 'esi', 'ebp', 'ebx'], [i.op_str for i in tail[:4]]
    assert tail[4].op_str == '0x%x' % MENU_TOP, '完事回菜单头 (与培养同一条收尾)'
    one('inc', 'dword ptr [0x%x]' % L['c_birth'])
    # 名字弹窗 = 原生 5 枚实参 (条目数/指针数组/样式/0/0), 分页后 11 行, 压在 12 硬门里
    # ★ 三次对话框: 选名 / 满员提示 / **出生提示** (2026-10-07 实机「生了孩子没有任何提示」)
    assert cnt('call', dl) == 3, '一次选名 + 满员提示 + 出生提示 (命中 %d)' % cnt('call', dl)
    assert cnt('add', 'esp, 0x14') == 3 and cntx('push', '4') == 4 and cntx('push', '0') == 6
    # 行数不是立即数: bn_show 把"页长 + 1 行导航"算在 edi 里再 push (与培养页同一套写法)
    assert cntx('mov', 'dword ptr [esp + 8], edi') == 1
    _dj = [k for k, i in enumerate(ins) if i.mnemonic == 'call' and i.op_str == dl][0]
    assert [(x.mnemonic, x.op_str) for x in ins[_dj - 5:_dj]] == \
        [('push', '0'), ('push', '0'), ('push', '4'), ('push', '0x%x' % L['sub_ptr']), ('push', 'edi')], \
        '选名弹窗必须是原生 5 枚实参 (样式 0/0 + flag 4 + 指针数组 + 条目数)'
    assert cnt('cmp', 'ax, -1') == 3, '取消 / 排程表两处哨兵'
    # 分页: 行 -> 池内第 k 个名字 (k*7 用 eax*8-eax, keystone 不支持 scale 7)
    one('lea', 'edx, [eax*8]')
    one('sub', 'edx, eax')
    one('add', 'edx, 0x%x' % L['name_pool'])
    one('mov', 'dword ptr [edi*4 + 0x%x], edx' % L['sub_ptr'])
    sa = 'word ptr [edi*2 + 0x%x]' % L['slot_arr']
    one('mov', sa, '0xfffe')
    one('mov', sa, '0xfffd')
    _sa = 'word ptr [eax*2 + 0x%x]' % L['slot_arr']
    one('movzx', 'edx', _sa)
    one('cmp', 'edx, 0xfffe')
    one('cmp', 'edx, 0xfffd')
    one('add', 'dword ptr [esp + 4], %s' % pm)
    one('sub', 'dword ptr [esp + 4], %s' % pm)
    # 空槽扫描: 位图没记 + 状态字 0x8080 (真空闲) + 从 4i 待登场区之后起
    one('bt', 'dword ptr [0x%x], ebx' % L['child_bm'])
    one('movzx', 'edx, word ptr [ecx + 0x2c]')
    one('and', 'edx, 0x8080')
    one('cmp', 'edx, 0x8080')
    one('mov', 'ebx, 0x%x' % L['slot_lo'])
    one('cmp', 'ebx, 0x%x' % L['cap'])
    # 空身份键: 从高往低吃 (低段是剧本在册的人), 且要没被排程表用过
    one('mov', 'ebx, 0x%x' % (BIRTH_OID_MAX - 1))
    one('cmp', 'byte ptr [ebx + 0x%x], 0' % L['flagtab'])
    one('cmp', 'eax, ebx')
    # 追排程表项 (oid/slot/fslot=主角 oid/国|城) + 把哨兵往后挪一格, 然后交 child_pass 实例化
    one('mov', 'word ptr [ebx], ax')
    one('mov', 'word ptr [ebx + 2], ax')
    one('mov', 'word ptr [ebx + 4], ax')
    one('mov', 'word ptr [ebx + 6], ax')
    one('mov', 'word ptr [ebx + 8], 0xffff')
    # 池槽 vs oid 是两个键空间: 排程表 fslot 与姓表行号用主角的**槽**(ent+0), 父链 +0x1d 用**oid**(ent+2)
    one('movzx', 'eax, word ptr [esi]')
    one('mov', 'dword ptr [esp + 0x1c], eax')
    _fs = ins.index(one('mov', 'eax, dword ptr [esp + 0x1c]'))
    assert ins[_fs + 1].mnemonic == 'mov' and ins[_fs + 1].op_str == 'word ptr [ebx + 4], ax', \
        'fslot 必须取主角的池槽 (place_child 拿它直接算 pool + slot*47)'
    _sx = ins.index(one('mov', 'edx, dword ptr [esp + 0x1c]'))
    assert ins[_sx + 1].op_str == 'esi, [edx*8]', '姓行索引必须取主角的池槽 (姓/名表 = 槽 x 7)'
    one('movzx', 'eax, word ptr [eax + 2]')
    _cp = ins.index(one('call', '0x%x' % L['child_pass']))
    assert cnt('call', '0x%x' % 0x47F7B0) == 0, '不自己 INST: 实例化只有 child_pass 那一条已验证的路'
    # 实例化之后再盖三样: 虚岁 1 的生年 / 父 = 主角 oid / 姓随父 + 名随玩家
    assert ins.index(one('add', 'eax, %s' % cap_imm(0x46))) > _cp, \
        '生年必须在 child_pass 之后写 (INST 会先抄记录里的生年)'
    one('mov', 'byte ptr [ecx + 0x1b], al')
    one('mov', 'word ptr [ecx + 0x1d], ax')
    # 姓/名两趟写表 (bcp_*) + 出生提示把两行读回来 (bp_*) = 姓表 2 趟、名表 2 趟
    assert cnt('mov', 'ecx, 7') == 4, '姓/名各写一趟 + 各读回一趟 (命中 %d)' % cnt('mov', 'ecx, 7')
    assert cnt('rep', 'movsb') == 0, '不用 rep movsb (不赌方向旗标)'
    assert cntx('dec', 'ecx') == 4, '四趟字节循环'
    _g = [i for i in ins if i.mnemonic == 'add' and i.op_str == 'esi, 0x%x' % L['giv']]
    assert len(_g) == 2, '姓表 esi: 父亲行(写源) + 孩子行(读回显示) 各一趟 (命中 %d)' % len(_g)
    # 名表 edi 基址有两处 (bcp_giv 写孩子行 / bn_live 扫描读行), 取前面那处核顺序
    _s = [k for k, i in enumerate(ins)
          if i.mnemonic == 'add' and i.op_str == 'edi, 0x%x' % L['sur']][0]
    assert all(i.address > _cp for i in _g) and _s > _cp, '姓/名覆盖必须在 child_pass 之后'
    # ---- 出生提示: 姓名两行拼成一个连续串, 三行指针数组落 BIRTH_PROMPT, 弹在**写表之后** ----
    one('mov', 'edi, 0x%x' % L['name_tmp'])                    # 拼串写游标
    one('mov', 'dword ptr [0x%x], 0x%x' % (L['msg_arr'],
                                           L['msg_str'] + MS_BORN * MS_STR_ROW))
    one('mov', 'dword ptr [0x%x], 0x%x' % (L['msg_arr'] + 4, L['name_tmp']))
    one('mov', 'dword ptr [0x%x], 0x%x' % (L['msg_arr'] + 8,
                                           L['msg_str'] + MS_BORN_AT * MS_STR_ROW))
    one('mov', 'dword ptr [0x%x], 0x%x' % (L['msg_arr'] + 12,
                                           L['msg_str'] + MS_BORN_GK * MS_STR_ROW))
    assert cntx('mov', 'byte ptr [edi], 0') == 2, '两趟循环都要有界收尾 (落空也补 NUL, 不越界读)'
    _pp = ins.index(one('push', '0x%x' % L['msg_arr']))
    assert ins[_pp + 1].mnemonic == 'push' and ins[_pp + 1].op_str == '4', '出生提示 = 4 行'
    assert ins[_pp + 2].mnemonic == 'call' and ins[_pp + 2].op_str == dl
    _pc = [i for i in ins if i.mnemonic == 'call' and i.op_str == dl][-1]
    assert _pc.address > _cp, '出生提示必须在实例化/写表之后 (否则名字还没落盘就显示)'
    assert _pc.address < ins[-1].address, '出生提示之后才能走收尾'
    # ---- v2: 本次可选表 bn_avail + 在世重名避让 bn_live (池 500 供 20, 选过不再出现) ----
    _loc = [i for i in ins if i.mnemonic == 'call'
            and origin <= int(i.op_str, 16) < origin + len(code)]
    assert len(_loc) == 2, '桩内只应有 bn_avail / bn_live 两次本地 call (命中 %d)' % len(_loc)
    _av, _lv = [int(i.op_str, 16) for i in _loc]
    assert _av < _lv and _loc[0].address < _loc[1].address, \
        'bn_avail 在前、bn_live 在后 (调用点与目标同序)'
    # 开框前收表: call bn_avail 必须在选名弹窗之前
    assert _loc[0].address < [i for i in ins if i.mnemonic == 'call' and i.op_str == dl][0].address, \
        'bn_avail 必须在弹窗之前 (AVAIL 空着就开框 = 列表什么都没有)'
    # 收表循环的两道界: 池长 (扫到头) 与本次供给量
    one('cmp', 'ebx, 0x%x' % BIRTH_NAME_COUNT)
    one('cmp', 'eax, 0x%x' % BIRTH_NAME_OFFER)
    # ★随机起点: 每次开框换个起点绕圈扫 (原生 rand(n) 只毁 eax/edx), ebp 数已扫格数 = 至多一整圈
    one('push', '0x%x' % BIRTH_NAME_COUNT)
    one('call', '0x%x' % CG.RAND)
    one('add', 'esp, 4')
    one('mov', 'ebx, eax')
    one('cmp', 'ebp, 0x%x' % BIRTH_NAME_COUNT)
    assert cntx('xor', 'ebx, ebx') == 1, '绕回池头只有扫过界时那一次'
    _rs = ins.index(one('mov', 'ebx, eax'))
    assert _rs > ins.index(one('call', '0x%x' % CG.RAND)), '随机起点必须先取 rand 再当游标'
    assert ins.index(one('call', '0x%x' % _av)) < _rs, 'bn_avail 在弹窗之前 (上面已核, 这里核 rand 也在框前)'
    # 三道门: 选过没有 / 有没有活人在用 / 收进表并计数
    one('cmp', 'byte ptr [ebx + 0x%x], 0' % L['used'])
    one('call', '0x%x' % _lv)
    one('mov', 'word ptr [eax*2 + 0x%x], bx' % L['avail'])
    assert cnt('inc', 'dword ptr [0x%x]' % L['avail_n']) == 1
    # 分页读表: 行号越界看 AVAIL_N (bn_fill 一处 + 下一页守卫一处), 行值 = 池内下标
    assert cnt('cmp', 'eax, dword ptr [0x%x]' % L['avail_n']) == 2, \
        'bn_fill 越界 + 下一页守卫 (命中 %d)' % cnt('cmp', 'eax, dword ptr [0x%x]' % L['avail_n'])
    one('movzx', 'eax', 'word ptr [eax*2 + 0x%x]' % L['avail'])
    # 选中的名字写进 USED, 且必须在实例化之前 (b_slot 之后就走创建流程了)
    _us = ins.index(one('mov', 'byte ptr [edx + 0x%x], 1' % L['used']))
    assert _us < _cp, 'USED 标记必须在 child_pass 之前 (点一次就该少一个候选)'
    # bn_live 的在岗门 = 点亮桩同一条: 0x8080 / 0x001B / 0x010F (掩码 0x879F)
    one('movzx', 'edx', 'word ptr [eax + 0x2c]')
    one('and', 'eax, 0x8080')
    one('cmp', 'eax, 0x8080')
    one('and', 'edx, %s' % cap_imm(0x879F))
    one('cmp', 'edx, %s' % cap_imm(0x1B))
    one('cmp', 'edx, %s' % cap_imm(0x10F))
    one('mov', 'eax, dword ptr [ecx + 3]')
    one('cmp', 'eax, dword ptr [edi + 3]')
    one('cmp', 'eax, dword ptr [edi]')
    # 名表 esi/edi 基址: bn_live 的行基址 + bcp_giv 的孩子行, 共两处
    assert cnt('add', 'edi, 0x%x' % L['sur']) == 2, \
        '名表 edi 基址 = 写表 1 处 + bn_live 扫描 1 处 (命中 %d)' % cnt('add', 'edi, 0x%x' % L['sur'])
    return ins


@echo off
rem PURE ASCII + CRLF - see StartTaikou2.bat for why.
rem M5 = end of M3c: one raise per month + gold cost + days advanced +
rem       progress rows on the panel + a small feedback box from the child.
rem   gate 1  once per month  (ym = (year<<8|month)+1, cnt < MONTHLY_CAP)
rem   gate 2  days: DATE_D + ACT_DAYS[act] <= 30  (0x1f would roll the month,
rem           and the month rollover chain calls our growth stub re-entrantly)
rem   gate 3  gold: days * 2, compare word[0x51662E] before paying (0x44E350)
rem   then     confirm box -> pay -> advance days (0x4A0D50 xN) -> push to RING
rem   panel    + progress rows: invested pts / dims raised / months to genpuku
rem            / raises left this month
rem   feedback kd_msg small box: child name + a per-activity line
rem   06d    3 real-machine fixes: rerun child_pass before scanning (roster no
rem          longer waits for the month rollover), the child line pops BEFORE
rem          0x4A0D50 (that call fires native daily events which used to hog
rem          the foreground), and the feedback box counts its own NUL because
rem          TextOutA with cbString -1 paints nothing on this build.
call "%~dp0StartTaikou2.bat" "%~dp0TAIK2W95_big_m5.exe"

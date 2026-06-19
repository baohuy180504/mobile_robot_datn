#!/usr/bin/env python3
"""
Script chan doan kieu "chia doi tim loi" - KHONG phai mot phan cua
web_control.py.

Da xac nhan: diag_minimal_read.py (khong dong vao termios) DOC DUOC.
web_control.py (co tu cau hinh termios) thi KHONG doc duoc gi ca.

Script nay test TUNG NHOM thay doi cau hinh trong web_control.py mot,
theo thu tu tang dan, de tim chinh xac nhom nao lam hong ket noi:

  Test 0: baseline da biet hoat dong tot (doi chieu, dam bao moi thu sach)
  Test 1: chi dat baud rate (ispeed/ospeed = B115200)
  Test 2: + cflag (CLOCAL, CREAD, tat PARENB/CSTOPB, bat CS8)
  Test 3: + tat CRTSCTS
  Test 4: + iflag (tat IXON/IXOFF/IXANY)
  Test 5: + lflag (tat ICANON/ECHO/ECHOE/ISIG)
  Test 6: + oflag (tat OPOST)              <- day la TOAN BO config
                                               giong web_control.py,
                                               TRU TIOCEXCL/O_NONBLOCK
  Test 7: Test 6 + them TIOCEXCL
  Test 8: Test 6 + mo bang O_NONBLOCK roi go bang fcntl (dung y het
          production code)

Giua MOI test, script tu dong chay `stty` de RESET cong ve dung baseline
da biet hoat dong tot, tranh ket qua bi nhieu lan nhau giua cac buoc.

CACH CHAY (dam bao web_control.py dang TAT han):

    python3 diag_binary_search.py
"""

import fcntl
import os
import select
import subprocess
import sys
import termios
import time

PORT = os.environ.get("AMR_ARDUINO_SERIAL_PORT", "/dev/arduino_mega")
READ_SECONDS = 2.0

RESET_CMD = [
    "stty", "-F", PORT,
    "115200", "raw", "-echo", "-crtscts",
    "cs8", "-cstopb", "-parenb", "clocal",
]


def reset_baseline():
    result = subprocess.run(RESET_CMD, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[diag] CANH BAO: reset baseline that bai: {result.stderr.strip()}")
    time.sleep(0.3)


def try_read(fd, label):
    collected = b""
    deadline = time.monotonic() + READ_SECONDS
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            ready, _, _ = select.select([fd], [], [], remaining)
        except OSError as exc:
            print(f"  -> LOI select(): {exc}")
            return False
        if not ready:
            continue
        try:
            chunk = os.read(fd, 256)
        except OSError as exc:
            print(f"  -> LOI read(): {exc}")
            return False
        if chunk:
            collected += chunk

    ok = b"e:" in collected
    status = "DOC DUOC" if ok else "IM LANG (loi)"
    print(f"  -> [{label}] {status} | {len(collected)} byte nhan duoc"
          + (f" | mau: {collected[:40]!r}" if collected else ""))
    return ok


def run_test(label, configure_fn, open_flags):
    reset_baseline()
    try:
        fd = os.open(PORT, open_flags)
    except OSError as exc:
        print(f"  -> [{label}] MO THAT BAI: {exc}")
        return False

    try:
        if configure_fn is not None:
            configure_fn(fd)
        ok = try_read(fd, label)
    finally:
        os.close(fd)
    return ok


def cfg_baud_only(fd):
    attrs = termios.tcgetattr(fd)
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def cfg_plus_cflag(fd):
    attrs = termios.tcgetattr(fd)
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    cflag = attrs[2]
    cflag |= (termios.CLOCAL | termios.CREAD)
    cflag &= ~termios.PARENB
    cflag &= ~termios.CSTOPB
    cflag &= ~termios.CSIZE
    cflag |= termios.CS8
    attrs[2] = cflag
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def cfg_plus_crtscts(fd):
    attrs = termios.tcgetattr(fd)
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    cflag = attrs[2]
    cflag |= (termios.CLOCAL | termios.CREAD)
    cflag &= ~termios.PARENB
    cflag &= ~termios.CSTOPB
    cflag &= ~termios.CSIZE
    cflag |= termios.CS8
    if hasattr(termios, "CRTSCTS"):
        cflag &= ~termios.CRTSCTS
    attrs[2] = cflag
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def cfg_plus_iflag(fd):
    attrs = termios.tcgetattr(fd)
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    cflag = attrs[2]
    cflag |= (termios.CLOCAL | termios.CREAD)
    cflag &= ~termios.PARENB
    cflag &= ~termios.CSTOPB
    cflag &= ~termios.CSIZE
    cflag |= termios.CS8
    if hasattr(termios, "CRTSCTS"):
        cflag &= ~termios.CRTSCTS
    attrs[2] = cflag

    iflag = attrs[0]
    iflag &= ~(termios.IXON | termios.IXOFF | termios.IXANY)
    attrs[0] = iflag

    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def cfg_plus_lflag(fd):
    attrs = termios.tcgetattr(fd)
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    cflag = attrs[2]
    cflag |= (termios.CLOCAL | termios.CREAD)
    cflag &= ~termios.PARENB
    cflag &= ~termios.CSTOPB
    cflag &= ~termios.CSIZE
    cflag |= termios.CS8
    if hasattr(termios, "CRTSCTS"):
        cflag &= ~termios.CRTSCTS
    attrs[2] = cflag

    iflag = attrs[0]
    iflag &= ~(termios.IXON | termios.IXOFF | termios.IXANY)
    attrs[0] = iflag

    lflag = attrs[3]
    lflag &= ~(termios.ICANON | termios.ECHO | termios.ECHOE | termios.ISIG)
    attrs[3] = lflag

    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def cfg_full_no_exclusive(fd):
    attrs = termios.tcgetattr(fd)
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    cflag = attrs[2]
    cflag |= (termios.CLOCAL | termios.CREAD)
    cflag &= ~termios.PARENB
    cflag &= ~termios.CSTOPB
    cflag &= ~termios.CSIZE
    cflag |= termios.CS8
    if hasattr(termios, "CRTSCTS"):
        cflag &= ~termios.CRTSCTS
    attrs[2] = cflag

    iflag = attrs[0]
    iflag &= ~(termios.IXON | termios.IXOFF | termios.IXANY)
    attrs[0] = iflag

    lflag = attrs[3]
    lflag &= ~(termios.ICANON | termios.ECHO | termios.ECHOE | termios.ISIG)
    attrs[3] = lflag

    oflag = attrs[1]
    oflag &= ~termios.OPOST
    attrs[1] = oflag

    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)


def cfg_full_plus_exclusive(fd):
    cfg_full_no_exclusive(fd)
    try:
        fcntl.ioctl(fd, termios.TIOCEXCL)
    except Exception as exc:
        print(f"  -> CANH BAO: TIOCEXCL that bai: {exc}")


def cfg_full_plus_nonblock_clear(fd):
    # fd duoc mo bang O_NONBLOCK o ngoai (xem open_flags cua test nay),
    # gio go no di dung y het production code.
    cfg_full_no_exclusive(fd)
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
    try:
        fcntl.ioctl(fd, termios.TIOCEXCL)
    except Exception as exc:
        print(f"  -> CANH BAO: TIOCEXCL that bai: {exc}")


def main():
    print(f"Cong: {PORT}")
    print(f"Lenh reset baseline: {' '.join(RESET_CMD)}")
    print("")

    print("Test 0: baseline da biet hoat dong tot (doi chieu)")
    run_test("Test0-baseline", None, os.O_RDWR | os.O_NOCTTY)
    print("")

    print("Test 1: chi dat baud rate")
    run_test("Test1-baud-only", cfg_baud_only, os.O_RDWR | os.O_NOCTTY)
    print("")

    print("Test 2: + cflag (CLOCAL/CREAD/CS8/tat parity+stopbit)")
    run_test("Test2-plus-cflag", cfg_plus_cflag, os.O_RDWR | os.O_NOCTTY)
    print("")

    print("Test 3: + tat CRTSCTS")
    run_test("Test3-plus-crtscts", cfg_plus_crtscts, os.O_RDWR | os.O_NOCTTY)
    print("")

    print("Test 4: + iflag (tat IXON/IXOFF/IXANY)")
    run_test("Test4-plus-iflag", cfg_plus_iflag, os.O_RDWR | os.O_NOCTTY)
    print("")

    print("Test 5: + lflag (tat ICANON/ECHO/ECHOE/ISIG)")
    run_test("Test5-plus-lflag", cfg_plus_lflag, os.O_RDWR | os.O_NOCTTY)
    print("")

    print("Test 6: + oflag (tat OPOST) - TOAN BO config (tru TIOCEXCL)")
    run_test("Test6-full-no-exclusive", cfg_full_no_exclusive, os.O_RDWR | os.O_NOCTTY)
    print("")

    print("Test 7: Test 6 + TIOCEXCL")
    run_test("Test7-full-plus-exclusive", cfg_full_plus_exclusive, os.O_RDWR | os.O_NOCTTY)
    print("")

    print("Test 8: giong production 100% (mo O_NONBLOCK, cau hinh, go O_NONBLOCK, TIOCEXCL)")
    run_test(
        "Test8-full-production-exact",
        cfg_full_plus_nonblock_clear,
        os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK,
    )
    print("")

    print("Dang reset cong ve baseline lan cuoi de don dep...")
    reset_baseline()
    print("Xong. Xem o tren: test nao dau tien hien 'IM LANG (loi)' chinh la")
    print("nguyen nhan - tat ca cac test SAU do se ke thua loi tuong tu.")


if __name__ == "__main__":
    main()
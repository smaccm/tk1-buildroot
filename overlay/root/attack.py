#!/usr/bin/env python

import sys
import curses
import re
import os
import random
import threading
import signal
from time import sleep
from mmap import mmap
from subprocess import call
from itertools import repeat

MIN_WIDTH = 95
UPPER_HEIGHT = 10
BYTES_PER_ROW = 16
ROW_LENGTH = 12 + 3 * BYTES_PER_ROW

BASE_ADDR = 0xd0000000
PAGE_SIZE = 0x1000

def range_length(base, len):
  return range(base, base + len)

KEY1 = range_length(0xd00004c8, 16)
KEY2 = range_length(0xd0001598, 16)

SALT1 = range_length(0xd000058c, 8)
SALT2 = range_length(0xd000165c, 8)

NONCE1 = range_length(0xd0000599, 8)
NONCE2 = range_length(0xd0001668, 8)

simulate = len(sys.argv) > 1
working = False
if simulate:
  working = sys.argv[1].lower() in ["true", "1", "yes", "t", "y"]

mem = {}

modified = threading.Event()
def simulateMemory():
  if not working:
    for addr in range(0, 2 * PAGE_SIZE):
      mem[addr] = chr(0)
    return

  for addr in range(0, 2 * PAGE_SIZE):
    mem[addr] = chr(random.randint(0, 255))

  nonce = random.randint(0, 256**3)
  while not modified.is_set():
    digits = []
    i = nonce
    for addr in NONCE1:
      mem[addr - BASE_ADDR] = chr(i % 256)
      i /= 256
    nonce += 1
    sleep(0.1)

if not simulate:
  dev_mem_fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
  mem = mmap(dev_mem_fd, 2 * PAGE_SIZE, offset=BASE_ADDR)
  for addr in range(0, 2 * PAGE_SIZE):
    if mem[addr] != chr(0):
      working = True
else:
  def exit(signal, frame):
    modified.set()
    sys.exit(0)
  signal.signal(signal.SIGINT, exit)
  threading.Thread(target=simulateMemory).start()

with open("banner.txt", "r") as f:
  banner = [line.rstrip() for line in f.readlines()]

def main(stdscr):
  my, mx = stdscr.getmaxyx()
  lower_height = max(7, my - UPPER_HEIGHT)
  width = max(MIN_WIDTH, mx)

  curses.curs_set(False)
  curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)
  GREEN = curses.color_pair(1)
  curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
  RED = curses.color_pair(2)

  upper_box = curses.newwin(UPPER_HEIGHT, width, 0, 0)
  upper_box.border(0)
  upper_box.addstr(0, 1, "Status")
  upper = curses.newwin(UPPER_HEIGHT - 2, width - 2, 1, 1)
  upper.scrollok(True)

  lower_box = curses.newwin(lower_height, width, UPPER_HEIGHT, 0)
  lower_box.border(0)
  lower_box.addstr(0, 1, "Memory")
  lower = curses.newwin(lower_height - 2, width - 2, UPPER_HEIGHT + 1, 1)
  lower.scrollok(True)

  stdscr.refresh()
  upper_box.refresh()
  lower_box.refresh()
  upper.refresh()
  lower.refresh()

  upper.addstr("Ready (press any key to continue)\n")
  upper.refresh()
  stdscr.getch()
  upper.addstr("Searching...\n")
  upper.refresh()
  stdscr.nodelay(1)

  top_addr = BASE_ADDR

  def y_to_addr(y):
    return top_addr + y * BYTES_PER_ROW

  def addr_to_yx(addr):
    y = 0
    offset = addr - top_addr
    while (offset >= BYTES_PER_ROW):
      offset -= BYTES_PER_ROW
      y += 1
    x = 12 + 3 * offset
    return (y, x)

  # Scroll to nonce
  for row in range(0, PAGE_SIZE / BYTES_PER_ROW):
    row_addr = BASE_ADDR + BYTES_PER_ROW * row
    lower.addstr("0x%08x: " % row_addr)

    for col in range(0, BYTES_PER_ROW):
      addr = row_addr + col;
      lower.addstr("%02x " % ord(mem[addr - BASE_ADDR]))

    lower.refresh()
    sleep(0.015)

    top_addr = row_addr - (lower_height - 3) * BYTES_PER_ROW
    
    focus = (lower_height - 3) * 2 / 3
    focus_addrs = range_length(y_to_addr(focus), BYTES_PER_ROW)

    if working and NONCE1[0] in focus_addrs:
      break
    lower.addstr("\n")

  def label(y, text):
    lower.addstr(y, ROW_LENGTH + 2, text, curses.A_BOLD)
    lower.refresh()

  def label_addr(addr, text):
    y, _ = addr_to_yx(addr)
    label(y, text)

  def refresh_data():
    for x_offset in range(0, BYTES_PER_ROW):
      for ry in range(0, lower_height - 2):
        rx = 12 + 3 * x_offset
        attr = curses.color_pair(lower.inch(ry, rx) >> 8)
        text = "%02x" % ord(mem[top_addr + x_offset + BYTES_PER_ROW * ry - BASE_ADDR])
        lower.addstr(ry, rx, text, attr)
    lower.refresh()

  def wait_for_key():
    while (stdscr.getch() == -1):
      refresh_data()
      sleep(0.1)

  def is_highlighted(y, x, color):
    return curses.color_pair(lower.inch(y, x) >> 8) == color

  def highlight_byte(addr, color):
    y, x = addr_to_yx(addr)
    lower.chgat(y, x, 2, color)
    if is_highlighted(y, x - 2, color):
      lower.chgat(y, x - 1, 1, color)
    lower.refresh()
    
  def highlight(block, color, text):
    y0, x0 = addr_to_yx(block[0])
    label(y0, text)
    
    for block_addr in block:
      highlight_byte(block_addr, color)
      refresh_data()
      sleep(0.1)

  def get_attrs(win, y_range, x_range):
    return [[curses.color_pair(win.inch(y, x) >> 8) for x in x_range] for y in y_range]

  def set_attrs(win, y_range, x_range, yx_attrs):
    for y, x_attrs in zip(y_range, yx_attrs):
      for x, attr in zip(x_range, x_attrs):
        win.chgat(y, x, 1, attr)

  def scan():
    for sy in range(0, lower_height - 2):
      attrs = get_attrs(lower, [sy], range(ROW_LENGTH - 1))
      set_attrs(lower, [sy], range(ROW_LENGTH - 1), repeat(repeat(GREEN)))
      refresh_data()
      sleep(0.05)
      set_attrs(lower, [sy], range(ROW_LENGTH - 1), attrs)
      for offset in range(0, BYTES_PER_ROW):
        addr = y_to_addr(sy) + offset
        if addr in KEY1 + SALT1:
          highlight_byte(addr, GREEN)
        if addr == KEY1[0]:
          label(sy, "crypto key")
        elif addr == SALT1[0]:
          label(sy, "crypto salt")

  def overwrite():
    # Overwrite decryption salt and nonce
    for addr in SALT1 + NONCE1:
      mem[addr - BASE_ADDR] = chr(0)
      modified.set()
      highlight_byte(addr, RED)
      if addr == SALT1[-1]:
        label_addr(SALT1[0], "crypto salt (modified)")
      if addr == NONCE1[-1]:
        label_addr(NONCE1[0], "crypto nonce (modified)")
      refresh_data()
      sleep(0.1)

    # Overwrite encryption salt and nonce too, but don't display it
    for addr in SALT2 + NONCE2:
      mem[addr - BASE_ADDR] = chr(0)

  if working:
    # Highlight nonce
    upper.addstr("Found nonce\n")
    upper.refresh()
    highlight(NONCE1, GREEN, "crypto nonce")
    wait_for_key()
    
    # Scan for salt and key
    upper.addstr("Searching nearby for salt and key\n")
    upper.refresh()
    scan()
    upper.addstr("Found and salt and key\n")
    upper.refresh()
    wait_for_key()
    
    # Overwrite salt and key
    upper.addstr("Overwriting salt and nonce\n")
    upper.refresh()
    overwrite()

  # Final status message
  if working:
    upper.addstr("Attack successful!", curses.A_BOLD)

    y, x = upper.getyx()
    upper.addstr("\n")
    upper.addstr("Press q to quit")
    upper.refresh()

    # Blink message highlighting
    prev_attrs = get_attrs(upper, [y], range(x))
    attrs = repeat(repeat(GREEN | curses.A_BOLD))
    while (stdscr.getch() != ord('q')):
      set_attrs(upper, [y], range(x), attrs)
      upper.refresh()
      prev_attrs, attrs = attrs, prev_attrs
      sleep(0.5)

  if not working:
    upper.addstr("Attacked failed!\n", curses.A_BOLD)
    upper.addstr("Press q to quit")
    upper.refresh()

    banner_length = max([len(line) for line in banner])
    banner_height = len(banner)
    popup_height = banner_height + 6
    popup_width = banner_length + 20
    text_x = (popup_width - banner_length) / 2
    text_y = (popup_height - banner_height) / 2
    popup_x = (mx - popup_width) / 2
    popup_y = (my - popup_height) / 2
    popup_box = curses.newwin(popup_height, popup_width, popup_y, popup_x)
    popup_box.border(0)
    for i, line in enumerate(banner):
      popup_box.addstr(i + text_y, text_x, line)
      popup_box.refresh()

    # Blink message
    background = 0
    while (stdscr.getch() != ord('q')):
      popup_box.bkgd(background)
      popup_box.refresh()
      background ^= RED
      sleep(0.5)

try:
  curses.wrapper(main)
finally:
  modified.set()

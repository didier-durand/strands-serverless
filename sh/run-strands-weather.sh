#!/usr/bin/env bash
ROOT_PATH=$(dirname $(dirname $(realpath $0)))
#
export PYTHONPATH="$ROOT_PATH/src"
echo "PYTHONPATH: $PYTHONPATH"
#

rm -rf "/tmp/.chainlit"
mkdir "/tmp/.chainlit"
cp "$ROOT_PATH/src/.chainlit/" "/tmp"
cd "$ROOT_PATH/src/strands_chainlit" || exit

export CHAINLIT_APP_ROOT="/tmp"
echo "CHAINLIT_APP_ROOT: $CHAINLIT_APP_ROOT"
export CHAINLIT_AUTH_SECRET="3q7.s1>zk*PRG46E,uip@03qOXY0CvCq.vuztOA7^-JuInv2l2hPv1TnfuV5bJzv"
chainlit run strands_weather.py

# for automated restart, use -w
# chainlit run strands_weather.py -w
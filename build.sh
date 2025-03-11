#!/bin/bash

if [ ! -d target ];then
mkdir -p target
fi

# copy 到 src
ls | grep -v target | grep -v build.sh | xargs -n1 -I {} cp -rf {} target

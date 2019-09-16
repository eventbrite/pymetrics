#!/bin/bash -ex

docker build -t pymetrics-test .

if [[ -z "$1" ]]
then
    docker run -it --rm pymetrics-test
else
    docker run -it --rm pymetrics-test tox "$@"
fi

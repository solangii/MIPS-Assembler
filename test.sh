#!/bin/bash

example_list='1 2 3 4 5 6 7'
#example_list='3'

for i in $example_list
do
    python assembler.py sample_input/example$i.s
    if cmp -s sample_input/example$i.o sample_output/example$i.o
    then
        echo "Success on example $i"
    else
        echo "Fail on example $i"
    fi
done

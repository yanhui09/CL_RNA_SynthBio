#!/anaconda3/envs/py35/bin/python
# # -*- coding: utf-8 -*-

"""design-ligandswitch.py: Design a multi-stable riboswitch similar to Hoehner 2013 paper."""

from __future__ import print_function

__author__ = "Stefan Hammer, Sven Findeiss"
__copyright__ = "Copyright 2018, Ribonets Project"
__credits__ = ["Stefan Hammer", "Sven Findeiss", "Ivo L. Hofacker",
                    "Christoph Flamm"]
__license__ = "GPLv3"
__version__ = "1.0"
__maintainer__ = "Stefan Hammer"
__email__ = "s.hamer@univie.ac.at"
__status__ = "Production"

import RNAblueprint as rbp
import argparse
import sys
import time

try:
    from RNAsketch import *
except ImportError as e:
    print( "Error: %s" % e , file=sys.stderr)
    exit(1)

def main():
    parser = argparse.ArgumentParser(description='Design a multi-stable riboswitch similar to Hoehner 2013 paper.')
    parser.add_argument("-f", "--file", type = str, default=None, help='Read file in *.inp format')
    parser.add_argument("-i", "--input", default=False, action='store_true', help='Read custom structures and sequence constraints from stdin')
    parser.add_argument("-q", "--package", type=str, default='vrna', help='Chose the calculation package: hotknots, pkiss, nupack, or vrna/ViennaRNA (default: vrna)')
    parser.add_argument("-j", "--objective", type=str, default='1', help='Chose the objective function: 1 for abs differences and 2 for squared (default: 1)')
    parser.add_argument("-T", "--temperature", type=float, default=37.0, help='Temperature of the energy calculations.')
    parser.add_argument("-n", "--number", type=int, default=4, help='Number of designs to generate')
    parser.add_argument("-s", "--stop", type=int, default=500, help='Stop optimization run if no better solution is aquired after (stop) trials.')
    parser.add_argument("-m", "--mode", type=str, default='random', help='Mode for getting a new sequence: sample, sample_plocal, sample_clocal, random')
    parser.add_argument("-k", "--kill", type=int, default=0, help='Timeout value of graph construction in seconds. (default: infinite)')
    parser.add_argument("-g", "--graphml", type=str, default=None, help='Write a graphml file with the given filename.')
    parser.add_argument("-c", "--csv", default=False, action='store_true', help='Write output as semi-colon csv file to stdout')
    parser.add_argument("-p", "--progress", default=False, action='store_true', help='Show progress of optimization')
    parser.add_argument("-d", "--debug", default=False, action='store_true', help='Show debug information of library')
    args = parser.parse_args()

    print("# Options: number={0:d}, stop={1:d}, mode={2:}, package={3:}, temperature={4:}".format(args.number, args.stop, args.mode, args.package, args.temperature))
    rbp.initialize_library(args.debug, args.kill)
    # define structures
    structures = []
    constraint = ''
    start_sequence = ''

    if (args.input):
        data = ''
        for line in sys.stdin:
            data = data + '\n' + line
        (structures, constraint, start_sequence) = read_input(data)
    elif (args.file is not None):
        print("# Input File: {0:}".format(args.file))
        (structures, constraint, start_sequence) = read_inp_file(args.file)
    else:
        structures = ['((((....))))....((((....))))........',
            '........((((....((((....))))....))))',
            '((((((((....))))((((....))))....))))']
        constraint = 'NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN'
    # try to construct dependency graph, catch errors and timeouts
    dg = None
    construction_time = 0.0
    sample_time = 0.0

    # construct dependency graph with these structures
    try:
        start = time.clock()
        dg = rbp.DependencyGraphMT(structures, constraint)
        construction_time = time.clock() - start
    except Exception as e:
        print( "Error: %s" % e , file=sys.stderr)

    # general DG values
    print("# " + "\n# ".join(structures) + "\n# " + constraint)

    if (dg is not None):

        # if requested write out a graphml file
        if args.graphml is not None:
            with open(args.graphml, 'w') as f:
                f.write(dg.get_graphml() + "\n")

        # print the amount of solutions
        print('# Maximal number of solutions: ' + str(dg.number_of_sequences()))
        # print the amount of connected components
        number_of_components = dg.number_of_connected_components()
        print('# Number of Connected Components: ' + str(number_of_components))
        for i in range(0, number_of_components):
            print('# [' + str(i) + ']' + str(dg.component_vertices(i)) + ' -> ' + str(dg.number_of_sequences(i)) + ' solutions')

        # remember general DG values
        graph_properties = get_graph_properties(dg)
        # create a initial design object
        design = get_Design(structures, start_sequence, args.package, args.temperature)

        # print header for csv file
        if (args.csv):
            print(";".join(["stop",
                        "mode",
                        "score",
                        "num_mutations",
                        "construction_time",
                        "sample_time",
                        design.write_csv_header()] +
                        graph_properties.keys()))

        # main loop from zero to number of solutions
        for n in range(0, args.number):
            # reset the design object
            design = get_Design(structures, start_sequence, args.package, args.temperature)

            start = time.clock()

            # now do the optimization based on the chose mode for args.stop iterations
            objective = calculate_objective
            if (args.objective == 2):
                objective = squared_objective

            try:
                (score, number_of_mutations) = adaptive_walk_optimization(dg, design, objective_function=objective, stop=args.stop, mode=args.mode, progress=args.progress)
            except ValueError as e:
                print (e.value)
                exit(1)
            # stop time counter
            sample_time = time.clock() - start

            if (args.csv):
                print(args.stop,
                        "\"" + args.mode + "\"",
                        score,
                        number_of_mutations,
                        construction_time,
                        sample_time,
                        design.write_csv(),
                        *graph_properties.values(), sep=";")
            else:
                print(design.write_out(score))
    else:
        print('# Construction time out reached!')

def squared_objective(design, weight=0.5):
    return calculate_objective_1(design) + weight * calculate_objective_2_squared(design)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# coding: utf-8

"""
Concatenate all alignment files of all families. Then,
group alignments by genome.

@author: GEM, Institut Pasteur
March 2017
"""

import os
import sys
import logging
import progressbar
import multiprocessing
from genomeAPCAT import utils

logger = logging.getLogger("align.post")


def post_alignment(fam_nums, all_genomes, prefix, outdir, dname, quiet):
    """
    After the alignment of all proteins by family:

    - concatenate all alignment files
    - group the alignment by genome

    Parameters
    ----------
    fam_nums : []
        list of family numbers
    all_genomes : []
        list of all genomes in dataset
    prefix : str
        path to ``aldir/<name of dataset>`` (used to get extraction, alignment and btr files easily)
    outdir : str
        path to output directory, containing Aldir and Listdir, and that will also contain Treedir
    dname : str
        name of dataset (used to name concat and grouped files, as well as tree folder)
    quiet : bool
        True if nothing must be sent to sdtout/stderr, False otherwise
    """
    all_alns, status = concat_alignments(fam_nums, prefix, quiet)
    treedir = os.path.join(outdir, "Phylo-" + dname)
    os.makedirs(treedir, exist_ok=True)
    launch_group_by_genome(all_genomes, all_alns, status, treedir, dname, quiet)


def concat_alignments(fam_nums, prefix, quiet):
    """
    Concatenate all family alignment files to a unique file

    Parameters
    ----------
    fam_nums : []
        list of family numbers
    prefix : str
        path to ``aldir/<name of dataset>`` (used to get extraction, alignment and btr files easily)
    quiet : bool
        True if nothing must be sent to sdtout/stderr, False otherwise

    Returns
    -------
    tuple
        (output, str) with:

        - output: path to file containing concatenation of all alignments
        - str: "OK" if concatenation file already exists, "Done" if just did concatenation
    """
    output = "{}-complete.cat.aln".format(prefix)
    if os.path.isfile(output):
        logger.info("Alignments already concatenated")
        logger.warning(("Alignments already concatenated in {}. Program will use "
                        "it for next steps").format(output))
        return output, "OK"
    logger.info("Concatenating all alignment files")
    list_files = ["{}-mafft-prt2nuc.{}.aln".format(prefix, num_fam) for num_fam in fam_nums]
    # Check that all files exist
    for f in list_files:
        if not os.path.isfile(f):
            logger.error("The alignment file {} does not exist. Please check the families you "
                         "want, and their corresponding alignment files".format(f))
            sys.exit(1)
    if quiet:
        utils.cat(list_files, output)
    else:
        utils.cat(list_files, output, title="Concatenation")
    return output, "Done"


def launch_group_by_genome(all_genomes, all_alns, status, treedir, dname, quiet):
    """
    Function calling group_by_genome in a pool, while giving information to user
    (time elapsed)

    Parameters
    ----------
    all_genomes : []
        list of all genomes in the dataset
    all_alns : str
        path to file containing all alignments concatenated
    status : str
        "OK" if concatenation file already existed before running, "Done" if just did concatenation
    treedir : str
        path to tree directory
    dname : str
        name of dataset
    quiet : bool
        True if nothing must be sent to sdtout/stderr, False otherwise
    """
    outfile = os.path.join(treedir, dname + ".grp.aln")
    if status == "Done":
        utils.remove(outfile)
    if os.path.isfile(outfile):
        logger.info("Alignments already grouped by genome")
        logger.warning(("Alignments already grouped by genome in {}. "
                        "Program will end. ").format(outfile))
        return
    logger.info("Grouping alignments per genome")
    bar = None
    if not quiet:
        widgets = [progressbar.BouncingBar(marker=progressbar.RotatingMarker(markers="◐◓◑◒")),
                   "  -  ", progressbar.Timer()]
        bar = progressbar.ProgressBar(widgets=widgets, max_value=20, term_width=50)
    pool = multiprocessing.Pool(1)
    args = [all_genomes, all_alns, outfile]
    final = pool.map_async(group_by_genome, [args], chunksize=1)
    pool.close()
    if not quiet:
        while True:
            if final.ready():
                break
            bar.update()
        bar.finish()
    pool.join()


def group_by_genome(args):
    """
    From the alignment file 'all_alns' containing all proteins, group the alignments of
    proteins by their genome (listed in 'all_genomes'), and save the result
    in 'treedir'

    Parameters
    ----------
    args : tuple
        - all_genomes: list of all genomes
        - all_alns: path to file containing all alignments concatenated
        - outfile: path to file which will contain alignments grouped by genome
    """
    all_genomes, all_alns, outfile = args
    sequences = read_alignments(all_alns, all_genomes)
    write_groups(outfile, sequences)


def read_alignments(all_alns, all_genomes):
    """
    Read alignment file, and assign each sequence to a genome

    Parameters
    ----------
    all_alns : str
        path to file containing all alignments concatenated
    all_genomes : []
        list of all genomes

    Returns
    -------
    dict
        {genome_name: [list of sequences for this genome]}
    """
    sequences = {}  # name: [list of sequences]
    genome = None
    seq = ""
    with open(all_alns, 'r') as alnf:
        for line in alnf:
            if line.startswith(">"):
                # If new header, write previous protein name/sequence to 'sequences'
                if genome and seq:
                    sequences[genome].append(seq)
                    seq = ""
                # Get new genome header
                genome = get_genome(line, all_genomes)
                if genome not in sequences:
                    sequences[genome] = []
            else:
                seq += line.strip()
    if genome and seq:
        sequences[genome].append(seq)
    per_genome = [len(seq) for seq in sequences.values()]
    if len(set(per_genome)) != 1:
        logger.error("Problems occurred while grouping alignments by genome: all genomes "
                     "do not have the same number of sequences. Check that each protein "
                     "name contains the name of the genome from which it comes.")
        sys.exit(1)
    logger.details("{} sequences found per genome".format(per_genome[0]))
    return sequences


def write_groups(outfile, sequences):
    """
    Writing alignments per genome to output file.

    Parameters
    ----------
    outfile : str
        path to file that will contain alignments grouped by genome
    sequences : dict
        {genome_name: [list of sequences (DNA, prot...) for this genome]}
    """
    logger.details("Writing alignments per genome")
    with open(outfile, "w") as outf:
        for genome in sorted(sequences, key=utils.sort_genomes):
            # write header for genome
            outf.write(">" + genome + "\n")
            # Write all sequences
            outf.write("".join(sequences[genome]) + "\n")


def get_genome(header, all_genomes):
    """
    Find to which genome belongs 'header'

    Parameters
    ----------
    header : str
        header read in alignment file
    all_genomes : []
        list of all genomes

    Returns
    -------
    str
        name of genome from which the header is
    """
    header = header.split(">")[1].split()[0]
    for genome in all_genomes:
        if genome in header:
            return genome
    logger.error(("Protein {} does not correspond to any genome name "
                  "given... {}").format(header, all_genomes))
    sys.exit(1)

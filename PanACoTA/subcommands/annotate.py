#!/usr/bin/env python3
# coding: utf-8

"""
annotate is a subcommand of PanACoTA

It is a pipeline to do quality control and annotate genomes. Steps are:

- optional: find stretches of at least 'n' N (default n=5), and cut into a new contig at this stretch
- for each genome, calc L90 and number of contigs (after cut at N stretches if used)
- keep only genomes with:

    - L90 <= x (default x = 100)
    - #contig <= y (default y = 999)
- rename those genomes and their contigs, with strain name increasing with quality (L90 and
  #contig)
- annotate kept genomes with prokka (default) or only prodigal
- gembase format

Input:

- **list_file:** list of genome filenames to annotate. This file contains 1 line per genome. It
  contains the name(s) of the (multi-)fasta file(s) corresponding to the genome (separated
  by space if several fasta files for the genome). After quality control, selected genomes
  will be named as following: ``<gen-spe>.<date>.<strain>``, with:

    * ``<gen_spe>`` 4 alphanumeric characters. Usually it corresponds to the 2 first letters
      of genus, and 2 first letters of species, like ESCO for Escherichia coli.
    * ``<date>`` date at which the genome was downloaded, formatted as MMYY (M=Month, Y=Year)
    * ``<strain>`` is the strain number of the genome in the species, ordered by quality.

Default values for ``<gen_spe>`` and ``<date>`` are given as input (see after). However, if some
genomes do not have the same date and/or genus/species as the others, you can add
this information for those genomes in the list file. fasta filenames and information are
separated by ``::``. ``<gen_spe>`` is given after the ``::``, and ``<date>`` is preceded by a
``.``. Here is an example::

    genome1.fasta
    genome2_ch1.fna genome2_pl.fst
    genome3.fst genome3_plasmid.fst :: name
    genome4.fna genome4.p1.fna genome4.p2.fna :: name.
    genome5.fasta :: name.date
    genome6.chromo.fst genome6.pl.fst  :: .date

- **species:** with 4 alphanumeric characters, used to rename genomes (except those whose
  species name is specified in the list file)
- **date:** optional. By default, takes the current date. Used to rename genomes (except those
  whose date is specified in the list file)
- **dbpath:** path to folder containing all multi-fasta sequences of genomes
- **respath:** path to folder where outputs must be saved (folders Genes, Replicons, Proteins,
  LSTINFO, gff3 and LSTINFO_dataset.lst file)
- **tmppath** optional. Path where tmp files must be saved. Default is respath/tmp_files
- **annotepath** optional. Path where prokka/prodigal output folders for all genomes must be saved.
  Default is respath/tmp_files
- **threads:** number of threads that can be used (default 1)

Output:

- In your given ``respath``, you will find 5 folders:

    * LSTINFO (information on each genome, with gene annotations),
    * Genes (nuc. gene sequences),
    * Proteins (aa proteins sequences),
    * Replicons (input sequences but with formatted headers).
    * gff3 (information on genes as gff3 format)

- In your given ``tmppath`` folder, folders with prokka/prodigal results will
  be created for each input genome (1 folder per genome, called
  ``<genome_name>-[prokka, prodigal]Res``). If errors are generated during prokka/prodigal
  step, you can look at the log file to see what was wrong
  (``<genome_name>-[prokka, prodigal].log``).
- In your given ``respath``, a file called ``annotate-genomes-<list_file>.log`` will be generated.
  You can find there all logs.
- In your given ``respath``, a file called ``annotate-genomes-<list_file>.log.err`` will be
  generated, containing information on errors and warnings that occurred: problems during
  annotation (hence no formatting step ran), and problems during formatting step. If this file is
  empty, then annotation and formatting steps finished without any problem for all genomes.
- In your given ``respath``, you will find a file called ``LSTINFO-<list_file>.lst`` with
 information on all genomes: gembase_name, original_name, genome_size, L90, nb_contigs
- In your given ``respath``, you will find a file called ``discarded-<list_file>.lst`` with
  information on genomes that were discarded (and hence not annotated) because of the
  L90 and/or nb_contig threshold: original_name, genome_size, L90, nb_contigs
- In your given ``respath``, you will find 2 png files: ``QC_L90-<list_file>.png`` and
  ``QC_nb-contigs-<list_file>.png``, containing the histograms of L90 and nb_contigs values for
  all genomes, with a vertical red line representing the limit applied here.

Requested:

- in prokka/prodigal results, all genes are called ``<whatever>_<number>``
   -> the number will be kept.
- The number of the genes annotated by prokka/prodigal are in increasing order
  in tbl, faa and ffn files
- genome names given to prokka/prodigal should not end with '_<number>'. Ideally, they should
  always have the same format: ``<spegenus>.<date>.<strain_number>`` but they can have
  another format, as long as they don't end by '_<number>', which is the format of a gene name.

@author gem
April 2017
"""

import os
import sys
from termcolor import colored


def main_from_parse(arguments):
    """
    Call main function from the arguments given by parser

    Parameters
    ----------
    arguments : argparse.Namespace
        result of argparse parsing of all arguments in command line

    """
    cmd = "PanACoTA " + ' '.join(arguments.argv)
    main(cmd, arguments.list_file, arguments.db_path, arguments.res_path, arguments.name,
         arguments.date, arguments.l90, arguments.nbcont, arguments.cutn, arguments.threads,
         arguments.force, arguments.qc_only, arguments.from_info, arguments.tmpdir,
         arguments.annotdir, arguments.verbose, arguments.quiet, arguments.prodigal_only,
         arguments.small)


def main(cmd, list_file, db_path, res_dir, name, date, l90=100, nbcont=999, cutn=5,
         threads=1, force=False, qc_only=False, from_info=None, tmp_dir=None, res_annot_dir=None,
         verbose=0, quiet=False, prodigal_only=False, small=False):
    """
    Main method, doing all steps:

    1. analyze genomes (nb contigs, L90, stretches of N...)
    2. keep only genomes with 'good' (according to user thresholds) L90 and nb_contigs
    3. rename genomes with strain number in decreasing quality
    4. annotate genome with prokka or only prodigal
    5. format annotated genomes

    If option '-Q': ends at step 2.
    If option '--info <genome_info file name>' option: starts at step 2

    verbosity:

    - defaut 0 : stdout contains INFO, stderr contains ERROR.
    - 1: stdout contains INFO, stderr contains WARNING and ERROR
    - 2: stdout contains (DEBUG), DETAIL and INFO, stderr contains WARNING and ERROR
    - >=15: Add DEBUG in stdout

    Parameters
    ----------
    list_file : str
        file containing the list of genome files, 1 genome per line, separated by a
        space if a genome is split in several fasta files. This file can also
        specify date and/or species information, according to the format described
        in documentation.
    db_path : str
        Path to the folder containing all the fasta files which will be annotated
    res_dir : str
        Path to the folder which will contain result folders and files
    name : str
        4 alpha numeric characters, describing the species (for example ESCO). Used by default
        if no species name is given in list_file line.
    date : str
        4 alpha numeric characters, defining the default date, for strains where it is not specified
        in the list_file
    l90 : int
        Max L90 allowed to keep a genome
    nbcont : int
        Max number of contigs allowed to keep a genome
    cutn : int
        cut at each stretch of this number of 'N'. Don't cut if equal to 0
    threads : int
        max number of threads to use
    force : bool
        If True, overwrite previous results, if False keep what is already calculated
    qc_only : bool
        If True, do only quality control, if False, also do annotation
    tmp_dir : str or None
        Path to folder where tmp files must be saved. None to use the default tmp folder
    res_annot_dir : str or None
        Path to folder where are the prokka/prodigal result folders for the genomes. None
        to use the default prokka/prodigal folder
    verbose : int
        verbosity:
        default (0): info in stdout, error and more in stderr
        1 = add warnings in stderr
        2 = like 1 + add DETAIL to stdout (by default only INFO)
        >15: add debug to stdout
    quiet : bool
        True if nothing must be sent to stdout/stderr, False otherwise
    prodigal_only : bool
        True -> run only prodigal. False -> run prokka

    Returns
    -------
    (genomes, kept_genomes, skipped, skipped_format) : tuple
        with:

        - genomes: dict with all genomes in list_file:
          {genome: [gembase_name, path_split_gembase, gsize, nbcont, L90]}
        - kept_genomes: dict with all genomes kept for annotation (same format as genomes)
        - skipped: list of genomes skipped because they had a problem in annotation step
        - skipped_format : list of genomes skipped because they had a problem in format step
    """
    # import needed packages
    import shutil
    import logging
    from PanACoTA.annotate_module import genome_seq_functions as gfunc
    from PanACoTA.annotate_module import prokka_prodigal_functions as pfunc
    from PanACoTA.annotate_module import general_format_functions as ffunc
    from PanACoTA import utils

    # Check that needed softs are installed
    prokka = utils.check_installed("prokka")
    prodigal = utils.check_installed("prodigal")
    if not qc_only:
        # If user using prokka: check prokka is installed and in the path
            if not prodigal_only and not prokka:
                print("Prokka is not installed. 'PanACoTA annotate' cannot run. Install prokka "
                      "to be able to annotate genomes. If you only need syntactical annotation, "
                      "check that prodigal is installed, and add '--prodigal' option.")
                sys.exit(1)
            if prodigal_only and not prodigal:
                print("Prodigal is not installed. 'PanACoTA annotate' cannot run. Install "
                      "prodigal to be able to annotate genomes. If you also need functional "
                      "annotation, check that prokka is installed, and remove '--prodigal' "
                      "option.")
                sys.exit(1)

    # By default, all tmp files (split sequences, renamed sequences, prokka/prodigal results) will
    # be saved in the given <res_dir>/tmp_files.
    # Create output (results, tmp...) directories if not already existing
    if not tmp_dir:
        tmp_dir = os.path.join(res_dir, "tmp_files")
    if not res_annot_dir:
        res_annot_dir = tmp_dir
    os.makedirs(res_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(res_annot_dir, exist_ok=True)

    # If force was set, remove result folders (Proteins, Replicons, Genes, LSTINFO, gff)
    if force:
        shutil.rmtree(os.path.join(res_dir, "LSTINFO"), ignore_errors=True)
        shutil.rmtree(os.path.join(res_dir, "Proteins"), ignore_errors=True)
        shutil.rmtree(os.path.join(res_dir, "Genes"), ignore_errors=True)
        shutil.rmtree(os.path.join(res_dir, "Replicons"), ignore_errors=True)
        shutil.rmtree(os.path.join(res_dir, "gff3"), ignore_errors=True)
    # If not --force, check that result folders do not already contain results
    else:
        utils.check_out_dirs(res_dir)

    # get only filename of list_file, without extension
    listfile_base = os.path.basename(os.path.splitext(list_file)[0])

    # Initialize logger
    # set level of logger: level is the minimum level that will be considered.
    if verbose <= 1:
        level = logging.INFO
    # for verbose = 2, ignore only debug
    if verbose >= 2 and verbose < 15:
        level = utils.detail_lvl() # int corresponding to detail level
    # for verbose >= 15, write everything
    if verbose >= 15:
        level = logging.DEBUG
    logfile_base = os.path.join(res_dir, "PanACoTA-annotate_" + listfile_base)
    logfile_base = utils.init_logger(logfile_base, level, name='', details=True,
                                verbose=verbose, quiet=quiet)
    logger = logging.getLogger('')
    logger.info("Command used\n \t > " + cmd)
    logger.info("Let's start!")

    # STEP 1. analyze genomes (nb contigs, L90, stretches of N...)
    # If already info on genome (--info <file> option), skip this step
    # If no info on genomes, read them and get needed information
    if not from_info:
        # Read genome names.
        # genomes = {genome: [spegenus.date]}
        genomes = utils.read_genomes(list_file, name, date, db_path, tmp_dir)
        if not genomes:
            logger.error(("We did not find any genome listed in {} in the folder {}. "
                          "Please check your list to give valid genome "
                          "names.").format(list_file, db_path))
            sys.exit(-1)
        # Get L90, nbcontig, size for all genomes, and cut at stretches of 'N' if asked
        # -> genome: [spegenus.date, path, size, nbcont, l90]
        gfunc.analyse_all_genomes(genomes, db_path, tmp_dir, cutn, prodigal_only,
                                  logger, quiet=quiet)
    # --info <filename> option given: read information (L90, nb contigs...) from this file.
    else:
        # genomes = {genome: [spegenus.date, path_to_splitSequence, size, nbcont, l90]}
        genomes = utils.read_genomes_info(from_info, name, date, db_path, tmp_dir)

    # STEP 2. keep only genomes with 'good' (according to user thresholds) L90 and nb_contigs
    # genomes = {genome: [spegenus.date, path_to_splitSequence, size, nbcont, l90]}
    # Plot L90 and nb_contigs distributions
    gfunc.plot_distributions(genomes, res_dir, listfile_base, l90, nbcont)
    # Get list of genomes kept (according to L90 and nbcont thresholds)
    kept_genomes = {genome: info for genome, info in genomes.items()
                    if info[-2] <= nbcont and info[-1] <= l90}
    # Write discarded genomes to a file
    utils.write_discarded(genomes, list(kept_genomes.keys()), list_file, res_dir)
    # If only QC, stop here.
    if qc_only:
        utils.write_discarded(genomes, [], list_file, res_dir, qc=True)
        logger.info("QC only done.")
        return genomes, kept_genomes
    # STEP 3. Rename genomes kept, ordered by decreasing quality
    gfunc.rename_all_genomes(kept_genomes)
    # kept_genomes = {genome: [gembase_name, path_split_gembase, gsize, nbcont, L90]}
    # Write lstinfo file (list of genomes kept with info on L90 etc.)
    utils.write_lstinfo(list_file, kept_genomes, res_dir)
    # STEP 4. Annotate all kept genomes
    results = pfunc.run_annotation_all(kept_genomes, threads, force, res_annot_dir,
                                       prodigal_only, small, quiet=quiet)
    import sys
    sys.exit(1)
    # List of genomes to format
    results_ok = [genome for (genome, ok) in results.items() if ok]
    # If no genome was ok, no need to format them. Just print that no genome was annotated,
    # end program.
    if not results_ok:
        logger.error("Error: No genome was correctly annotated, no need to format them.")
        return
    # list of genomes skipped because annotation had problems: no format step run
    skipped = [genome for (genome, ok) in results.items() if not ok]
    # At least 1 genome was not annotated: write a message to warn on it
    if skipped:
        utils.write_warning_skipped(skipped, prodigal_only=prodigal_only,
                                    logfile=logfile_base)
    # Initialize list of genomes skipped because something went wrong while formatting.
    skipped_format = []

    # STEP 5. Format genomes annotated
    # Here, we have at least 1 genome annotated (otherwise,
    # it would already have stopped because results_ok is empty)
    # Generate database (folders Proteins, Genes, Replicons, LSTINFO)
    skipped_format = ffunc.format_genomes(genomes, results_ok, res_dir, res_annot_dir,
                                                  prodigal_only, threads, quiet=quiet)
    # At least one genome could not be formatted -> warn user
    if skipped_format:
        utils.write_warning_skipped(skipped_format, do_format=True, prodigal_only=prodigal_only,
                                    logfile = logfile_base)
    logger.info("Annotation step done.")


def build_parser(parser):
    """
    Method to create a parser for command-line options

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The parser to configure

    """
    import argparse
    from PanACoTA import utils

    def gen_name(param):
        if not utils.check_format(param):
            msg = ("The genome name must contain 4 characters. For example, this name can "
                   "correspond to the 2 first letters of genus, and 2 first letters of "
                   "species, e.g. ESCO for Escherichia Coli.")
            raise argparse.ArgumentTypeError(msg)
        return param

    def date_name(param):
        if not utils.check_format(param):
            msg = ("The date must contain 4 characters. Usually, it contains 4 digits, "
                   "corresponding to the month (2 digits) and year (2 digits).")
            raise argparse.ArgumentTypeError(msg)
        return param

    def get_date():
        import time
        return time.strftime("%m%y")

    def cont_num(param):
        try:
            param = int(param)
        except Exception:
            msg = "argument --nbcont: invalid int value: {}".format(param)
            raise argparse.ArgumentTypeError(msg)
        if param < 0:
            msg = "The maximum number of contigs allowed must be a positive number."
            raise argparse.ArgumentTypeError(msg)
        if param >= 10000:
            msg = "We do not support genomes with more than 9999 contigs."
            raise argparse.ArgumentTypeError(msg)
        return param

    # Create command-line parser for all options and arguments to give
    required = parser.add_argument_group('Required arguments')
    required.add_argument(dest="list_file",
                          help=("File containing the list of genome filenames to annotate (1 genome"
                                " per line). Each genome is in multi-fasta format. You can "
                                "specify the species name (4 characters) you want to give to each "
                                "genome by adding it after the genome filename(s), separated "
                                "by '::'. If not given, the species name will be the one given in "
                                "'species' argument. You can also specify the date (4 digits) "
                                "by adding '.' + your date choice after the genome "
                                "filename(s), '::' and, if given, the species name."))
    required.add_argument("-d", dest="db_path", required=True,
                          help="Path to folder containing all multifasta genome files")
    required.add_argument("-r", dest="res_path", required=True,
                          help="Path to folder where output annotated genomes must be saved")
    optional = parser.add_argument_group('Optional arguments')
    optional.add_argument("-n", dest="name", type=gen_name,
                          help=("Choose a name for your annotated genomes. This name should "
                                "contain 4 alphanumeric characters. Generally, they correspond "
                                "to the 2 first letters of genus, and 2 first letters of "
                                "species, e.g. ESCO for Escherichia Coli."))
    optional.add_argument("-Q", dest="qc_only", action="store_true", default=False,
                          help="Add this option if you want only to do quality control on your "
                               "genomes (cut at 5N if asked, calculate L90 and number of contigs "
                               "and plot their distributions). This allows you to check which "
                               "genomes would be annotated with the given parameters, and to "
                               "modify those parameters if you want, before you launch the "
                               "annotation and formatting steps.")
    optional.add_argument("--info", dest="from_info",
                          help="If you already ran the 'prepare' data module, or already "
                               "calculated yourself the L90 and number of contigs for each "
                               "genome, you can give this information, to go directly to "
                               "annotation and formatting steps. This file contains at "
                               "least 4 columns, tab separated, with the following headers: "
                               "'orig_name', 'gsize', 'nb_conts', 'L90'. Any other column "
                               "will be ignored.")
    optional.add_argument("--prodigal", dest="prodigal_only", action="store_true", default=False,
                          help="Add this option if you only want syntactical annotation, given "
                               "by prodigal, and not functional annotation requiring prokka and "
                               "is slower.")
    optional.add_argument("--l90", dest="l90", type=int, default=100,
                          help="Maximum value of L90 allowed to keep a genome. Default is 100.")
    optional.add_argument("--nbcont", dest="nbcont", type=cont_num, default=999,
                          help=("Maximum number of contigs allowed to keep a genome. "
                                "Default is 999."))
    optional.add_argument("--cutN", dest="cutn", type=int, default=5,
                          help=("By default, each genome will be cut into new contigs when "
                                "at least 5 'N' at a stretch are found in its sequence. "
                                "If you don't want to "
                                "cut genomes into new contigs when there are stretches of 'N', "
                                "put 0 to this option. If you want to cut from a different number "
                                "of 'N' stretches, put this value to this option."))
    optional.add_argument("--date", dest="date", default=get_date(), type=date_name,
                          help=("Specify the date (MMYY) to give to your annotated genomes. "
                                "By default, will give today's date. The only requirement on the"
                                " given date is that it is 4 characters long. You can use letters"
                                " if you want. But the common way is to use 4 digits, "
                                "corresponding to MMYY."))
    optional.add_argument("--tmp", dest="tmpdir",
                          help=("Specify where the temporary files (sequence split by stretches "
                                "of 'N', sequence with new contig names etc.) must be saved. "
                                "By default, it will be saved in your "
                                "result_directory/tmp_files."))
    optional.add_argument("--annot_dir", dest="annotdir",
                          help=("Specify in which directory the prokka/prodigal output files "
                                "(1 folder per genome, called "
                                "<genome_name>-[prokka, Prodigal]Res) must be "
                                "saved. By default, they are saved in the same directory as "
                                "your temporary files (see --tmp option to change it)."))
    optional.add_argument("-F", "--force", dest="force", action="store_true",
                          help=("Force run: Add this option if you want to (re)run annotation and "
                                "formatting steps for all genomes "
                                "even if their result folder (for annotation step) or files (for "
                                "format step) already exist: override existing results.\n"
                                "Without this option, if there already are results in the given "
                                "result folder, the program stops. If there are no results, but "
                                "prokka/prodigal folder already exists, prokka/prodigal won't run "
                                "again, and the formating step will use the already existing "
                                "folder if correct, or skip the genome if there are problems in "
                                "prokka/prodigal folder."))
    optional.add_argument("--small", dest="small", action="store_true", default=False,
                          help=("If you use Prodigal to annotate genomes, if you sequences are "
                                "too small (less than 20000 characters), it cannot annotate them "
                                "with the default options. Add this to use 'meta' procedure."))
    optional.add_argument("--threads", dest="threads", type=int, default=1,
                          help="Specify how many threads can be used (default=1)")
    helper = parser.add_argument_group('Others')
    helper.add_argument("-v", "--verbose", dest="verbose", action="count", default=0,
                        help="Increase verbosity in stdout/stderr.")
    helper.add_argument("-q", "--quiet", dest="quiet", action="store_true", default=False,
                        help=("Do not display anything to stdout/stderr. log files will "
                              "still be created."))
    helper.add_argument("-h", "--help", dest="help", action="help",
                        help="show this help message and exit")


def parse(parser, argu):
    """
    arse arguments given to parser

    Parameters
    ----------
    parser : argparse.ArgumentParser
        the parser used
    argu : [str]
        command-line given by user, to parse using parser

    Returns
    -------
    argparse.Namespace
        Parsed arguments
    """
    args = parser.parse_args(argu)
    return check_args(parser, args)


def check_args(parser, args):
    """
    Check that arguments given to parser are as expected.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The parser used to parse command-line
    args : argparse.Namespace
        Parsed arguments

    Returns
    -------
    argparse.Namespace or None
        The arguments parsed, updated according to some rules. Exit program
        with error message if error occurs with arguments given.

    """

    # Message if user kept default thresholds for L90 and nbcont. Just to warn him, to be sure
    # it was on purpose
    def thresholds_message(l90, nbcont):
        return ("  !! Your genomes will be filtered, and only the ones with 'L90' <= {} "
                "and 'number of contigs' < {} will be kept. If you want to change those "
                "thresholds, use '--l90' and '--nbcont' "
                "options.".format(args.l90, args.nbcont))

    # Message if user is giving a file with already calculated information
    def nosplit_message():
        split = ("  !! -> Your sequences will be used as is by PanACoTA. Be sure you already "
                 "split your sequences at each stretch of X 'N' if needed.\n")
        trust = ("     -> PanACoTA will use the values (L90, nbcont) given in your info file. "
                 "It will ignore the genomes for which those values are incorrect. "
                 "It will also ignore genomes with more than 999 contigs.")
        return split + trust

    #  ERRORS
    # User wants to run all annotation step: needs a genome dataset name
    if not args.qc_only and not args.name:
        parser.error("You must specify your genomes dataset name in 4 characters with "
                     "'-n name' option (type -h for more information). Or, if you do not want "
                     "to annotate and format your genomes but just to run quality control, use "
                     "option '-Q")
    # If QC only, we do not need name -> name is NONE
    if args.qc_only and not args.name:
        args.name = "NONE"
    # Cannot be verbose and quiet at the same time
    if args.verbose > 0 and args.quiet:
        parser.error("Choose between a verbose output (-v) or a quiet output (-q)."
                     " You cannot have both.")
    # option --small used only with prodigal
    if not args.prodigal_only and args.small:
        parser.error("You cannot use --small option with prokka. Either use prodigal, "
                     "or remove this option.")
    # If user specifies a cutN value (different than default one which is 5), and give
    # an info file, it is not compatible: info file will use sequences as is, and won't cut them
    if args.cutn != 5 and args.from_info:
        parser.error("If you provide a list of genomes with their calculated L90 and number of "
                     "contigs, PanACoTA will use the given sequences as is. It will not cut "
                     "them. So, you cannot use both --cutN and --info")

    # WARNINGS
    # If user wants to cur genomes, warn him to check that it is on purpose (because default is cut at each 5'N')
    if args.cutn != 0 and not args.from_info:
        message = ("  !! Your genomes will be split when sequence contains at "
                   "least {}'N' at a stretch.").format(args.cutn)
        print(colored(message, "yellow"))
    # Warn user about selection of genomes thresholds
    if args.l90 == 100 or args.nbcont == 999:
        print(colored(thresholds_message(args.l90, args.nbcont), "yellow"))
        if args.from_info:
            print(colored(nosplit_message(), "yellow"))
    print()
    return args


if __name__ == '__main__':
    import argparse
    from textwrap import dedent
    header = '''
     ___                 _____  ___         _____  _____
    (  _`\              (  _  )(  _`\      (_   _)(  _  )
    | |_) )  _ _   ___  | (_) || ( (_)   _   | |  | (_) |
    | ,__/'/'_` )/' _ `\|  _  || |  _  /'_`\ | |  |  _  |
    | |   ( (_| || ( ) || | | || (_( )( (_) )| |  | | | |
    (_)   `\__,_)(_) (_)(_) (_)(____/'`\___/'(_)  (_) (_)


       Large scale comparative genomics tools

     -------------------------------------------
     '''
    my_parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                        description=dedent(header), add_help=False)
    build_parser(my_parser)
    OPTIONS = parse(my_parser, sys.argv[1:])
    main_from_parse(OPTIONS)

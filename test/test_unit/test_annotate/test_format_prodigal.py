#!/usr/bin/env python3
# coding: utf-8

"""
Unit tests for general_format_functions.py
"""

import os
import logging
import shutil
from io import StringIO
import pytest

import PanACoTA.annotate_module.format_prodigal as prodigalfunc
import PanACoTA.utils as utils
import test.test_unit.utilities_for_tests as tutil

ANNOTEDIR = os.path.join("test", "data", "annotate")
GENOMES_DIR = os.path.join(ANNOTEDIR, "genomes")
EXP_ANNOTE = os.path.join(ANNOTEDIR, "exp_files")
TEST_ANNOTE = os.path.join(ANNOTEDIR, "test_files")
GENEPATH = os.path.join(ANNOTEDIR, "generated_by_unit-tests")

LOGFILE_BASE = os.path.join(GENEPATH, "logs", "logfile")
LOGFILES = [LOGFILE_BASE + ext for ext in [".log", ".log.debug", ".log.details", ".log.err"]]

@pytest.fixture(autouse=True)
def setup_teardown_module():
    """
    Remove log files at the end of this test module

    Before each test:
    - init logger
    - create directory to put generated files

    After:
    - remove all log files
    - remove directory with generated results
    """
    os.mkdir(GENEPATH)
    # utils.init_logger(LOGFILE_BASE, 0, 'test_fastme', verbose=1)
    print("setup")

    yield
    # shutil.rmtree(GENEPATH)
    # for f in LOGFILES:
    #     if os.path.exists(f):
    #         os.remove(f)
    print("teardown")


def test_create_gen_lst(caplog):
    """
    Check that generated gen and lst files are as expected.
    In the test file, all genomes have names different from gembase name
    This test file contains the following aspects:
    - gene in D strand (start < end)
    - gene in C strand (start > end)
    - CDS features
    - contigs with more than 2 genes
    - contig with only 2 genes (both 'b' loc)
    - contig with 1 gene ('b' loc)
    - contig without gene (should be skipped)
    """
    caplog.set_level(logging.DEBUG)
    logger = logging.getLogger("test_prodigal")
    genfile = os.path.join(TEST_ANNOTE, "original_name.fna-prodigalRes", "prodigal_out_for_test.faa")
    # contigs = ["test.0417.00002.0001\t50", "test.0417.00002.0002\t50", "test.0417.00002.0003\t50",
    #            "test.0417.00002.0004\t50", "test.0417.00002.0005\t50", "test.0417.00002.0006\t50",
    #            "test.0417.00002.0007\t50"]
    contigs = {"JGIKIPgffgIJ": "test.0417.00002.0001",
               "toto": "test.0417.00002.0002",
               "other_header": "test.0417.00002.0003",
               "my contig": "test.0417.00002.0004",
               "bis": "test.0417.00002.0005",
               "ter": "test.0417.00002.0006",
               "contname": "test.0417.00002.0007"
               }
    name = "test.0417.00002"
    res_gen_file = os.path.join(GENEPATH, "prodigal_res.gen")
    res_lst_file = os.path.join(GENEPATH, "prodigal_res.lst")
    gpath = "original_genome_name"
    assert prodigalfunc.create_gene_lst(contigs, genfile, res_gen_file, res_lst_file, gpath, name, logger)
    exp_lst = os.path.join(EXP_ANNOTE, "res_create_gene_lst_prodigal.lst")
    assert tutil.compare_order_content(exp_lst, res_lst_file)


def test_create_gen_lst_cont_unknown(caplog):
    """
    A contig name in the gen file does not exist -> error message, and all result files must be removed for this genome
    """
    caplog.set_level(logging.DEBUG)
    logger = logging.getLogger("test_prodigal")
    genfile = os.path.join(TEST_ANNOTE, "original_name.fna-prodigalRes", "prodigal_out_for_test.faa")
    contigs = {"JGIKIPgffgIJ": "test.0417.00002.0001",
               "toto": "test.0417.00002.0002",
               "other_header": "test.0417.00002.0003",
               "my_contig": "test.0417.00002.0004",
               "bis": "test.0417.00002.0005",
               "ter": "test.0417.00002.0006",
               "contname": "test.0417.00002.0007"
               }
    name = "test.0417.00002"
    res_gen_file = os.path.join(GENEPATH, "prodigal_res.gen")
    res_lst_file = os.path.join(GENEPATH, "prodigal_res.lst")
    gpath = "original_genome_name"
    assert not prodigalfunc.create_gene_lst(contigs, genfile, res_gen_file, res_lst_file, gpath, name, logger)
    assert ("my contig fount in test/data/annotate/test_files/original_name.fna-prodigalRes/prodigal_out_for_test.faa "
            "does not exist in original_genome_name")


def test_create_gen_lst(caplog):
    """
    Check that generated gen and lst files are as expected.
    In the test file, all genomes have names different from gembase name
    This test file contains the following aspects:
    - gene in D strand (start < end)
    - gene in C strand (start > end)
    - CDS features
    - contigs with more than 2 genes
    - contig with only 2 genes (both 'b' loc)
    - contig with 1 gene ('b' loc)
    - contig without gene (should be skipped)
    """
    caplog.set_level(logging.DEBUG)
    logger = logging.getLogger("test_prodigal")
    genfile = os.path.join(TEST_ANNOTE, "original_name.fna-prodigalRes", "prodigal_out_for_test.gff")
    # contigs = ["test.0417.00002.0001\t50", "test.0417.00002.0002\t50", "test.0417.00002.0003\t50",
    #            "test.0417.00002.0004\t50", "test.0417.00002.0005\t50", "test.0417.00002.0006\t50",
    #            "test.0417.00002.0007\t50"]
    contigs = {"JGIKIPgffgIJ": "test.0417.00002.0001",
               "toto": "test.0417.00002.0002",
               "other_header": "test.0417.00002.0003",
               "my contig": "test.0417.00002.0004",
               "bis": "test.0417.00002.0005",
               "ter": "test.0417.00002.0006",
               "contname": "test.0417.00002.0007"
               }
    name = "test.0417.00002"
    res_gen_file = os.path.join(GENEPATH, "prodigal_res.gen")
    res_lst_file = os.path.join(GENEPATH, "prodigal_res.lst")
    gpath = "original_genome_name"
    assert prodigalfunc.create_gene_lst(contigs, genfile, res_gen_file, res_lst_file, gpath, name, logger)
    exp_lst = os.path.join(EXP_ANNOTE, "res_create_gene_lst_prodigal.lst")
    assert tutil.compare_order_content(exp_lst, res_lst_file)

# # def test_tbl_to_lst_not_changed_names(caplog):
#     """
#     Check that generated lstinfo file is as expected, when the genome name is the same as
#     it already was in the genome given to prokka.
#     The test tblfile contains the following aspects:
#     - gene in D strand (start < end)
#     - gene in C strand (start > end)
#     - CDS features (some with all info = ECnumber, gene name, product etc. ;
#     some with missing info)
#     - tRNA type
#     - repeat_region type (*2)
#     - contigs with more than 2 genes
#     - contig with only 2 genes (both 'b' loc)
#     - contig with 1 gene ('b' loc)
#     - contig without gene (should be skipped)
#     """
#     caplog.set_level(logging.DEBUG)
#     logger = logging.getLogger("test_prokka")
#     tblfile = os.path.join(TEST_ANNOTE, "original_name.fna-prokkaRes", "prokka_out_for_test.tbl")
#     lstfile = os.path.join(GENEPATH, "res_test_tbl2lst.lst")
#     contigs = ["test.0417.00002.0001\t50", "test.0417.00002.0002\t50", "test.0417.00002.0003\t50",
#                "test.0417.00002.0004\t50", "test.0417.00002.0005\t50", "test.0417.00002.0006\t50",
#                "test.0417.00002.0007\t50"]
#     name = "test.0417.00002"
#     assert prokkafunc.tbl2lst(tblfile, lstfile, contigs, name, logger, changed_name=False)
#     exp_lst = os.path.join(EXP_ANNOTE, "res_tbl2lst.lst")
#     assert tutil.compare_order_content(exp_lst, lstfile)


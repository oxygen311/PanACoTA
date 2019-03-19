#!/usr/bin/env python3
# coding: utf-8

"""
Tests for make script, installing PanACoTA according to already existing dependencies
From a computer with ubuntu, prokka and quicktree installed
"""
import os
import pytest
import glob

from . import utilities as utils

@pytest.fixture
def install_panacota():
    cmd = "python3 make"
    error = "Error installing"
    utils.run_cmd(cmd, error)


def teardown_function(function):
    """
    Uninstall genomeAPCAT and installed dependencies at the end of each test
    """
    print("TEARDOWN\n")
    cmd = "python3 make uninstall"
    error = "Error uninstall"
    utils.run_cmd(cmd, error)
    os.remove("install.log")
    print("cleaning repo")


def test_install_prokka_quicktree():
    """
    Test that when installing from a computer containing only prokka and quicktree, it installs
    PanACoTA, and returns the list of missing dependencies
    """
    assert not utils.check_installed("barrnap")
    assert not utils.check_installed("prodigal")
    assert utils.check_installed("prokka")
    assert not utils.check_installed("genomeAPCAT")
    assert utils.check_installed('quicktree')
    cmd = "python3 make"
    error = "Error trying to install genomeAPCAT from base"
    utils.run_cmd(cmd, error)
    assert not utils.check_installed("barrnap")
    assert utils.check_installed("prokka")
    assert utils.check_installed("genomeAPCAT")
    assert utils.check_installed('quicktree')
    cmd = "pip3 show genomeAPCAT"
    err = "error pip3"
    stdout = "stdout_pip3show.out"
    with open(stdout, "w") as stdof:
        utils.run_cmd(cmd, err, stdout=stdof, stderr=stdof)
    with open(stdout, "r") as stdof:
        for line in stdof:
            if line.startswith("Location"):
                loc = line.split()[-1]
                assert glob.glob(os.path.join(loc, r'genomeAPCAT*dist-info'))
    os.remove(stdout)
    logfile = "install.log"
    content = ["Installing genomeAPCAT...", "DONE",
               "Some dependencies needed for some subcommands of genomeAPCAT are "
               "not installed. Here is the list of missing dependencies, and for what they are "
               "used. If you plan to use the subcommands hereafter, first install required "
               "dependencies:",
               "- mmseqs (for pangenome subcommand)",
               "- mafft (to align persistent genomes in order to infer a phylogenetic tree "
               "after)",
               "See more information on how to download/install those softwares in README or in "
               "documentation.",
               "- prodigal : for annotate subcommand, you at least need prodigal (for syntaxic "
               "annotation only). If you even need functional annotation, also install prokka"]
    with open(logfile, "r") as logf:
        logf_content = "".join(logf.readlines())
        for linec in content:
            assert linec in logf_content
    # Check that needed packages are installed
    assert utils.is_package_installed("argparse")
    assert utils.is_package_installed("progressbar")
    assert utils.is_package_installed("numpy")
    assert utils.is_package_installed("matplotlib")
    assert utils.is_package_installed("Bio")
    os.remove(logfile)


def test_upgrade(install_panacota):
    """
    Test upgrading genomeAPCAT when dependencies are still installed
    """
    assert not utils.check_installed("barrnap")
    assert utils.check_installed("prokka")
    assert utils.check_installed("genomeAPCAT")
    assert utils.check_installed('quicktree')
    cmd = "python3 make upgrade"
    error = "Error upgrade"
    utils.run_cmd(cmd, error)
    assert not utils.check_installed("barrnap")
    assert utils.check_installed("prokka")
    assert utils.check_installed("genomeAPCAT")
    assert utils.check_installed('quicktree')
    logfile = "install.log"
    with open(logfile, "r") as logf:
        lines = logf.readlines()
        assert len(lines) == 2
        assert "Upgrading genomeAPCAT" in lines[0]
        assert "DONE" in lines[1]


def test_uninstall_withdep(install_panacota):
    """
    Test uninstalling genomeAPCAT when dependencies are still installed
    """
    assert not utils.check_installed("barrnap")
    assert utils.check_installed("prokka")
    assert utils.check_installed("genomeAPCAT")
    cmd = "python3 make uninstall"
    error = "Error uninstalling"
    utils.run_cmd(cmd, error)
    assert not utils.check_installed("barrnap")
    assert utils.check_installed("prokka")
    assert not utils.check_installed("genomeAPCAT")
    assert utils.check_installed('quicktree')


def test_develop():
    """
    Test installing genomeAPCAT in developer mode, when prokka and barrnap are already installed
    """
    assert not utils.check_installed("genomeAPCAT")
    assert not utils.check_installed("barrnap")
    assert utils.check_installed('quicktree')
    assert utils.check_installed("prokka")
    cmd = "python3 make develop"
    error = "Error develop"
    utils.run_cmd(cmd, error)
    assert not utils.check_installed("barrnap")
    assert utils.check_installed("prokka")
    assert utils.check_installed("genomeAPCAT")
    assert utils.check_installed('quicktree')
    cmd = "pip3 show genomeAPCAT"
    err = "error pip3"
    stdout = "stdout_pip3show.out"
    with open(stdout, "w") as stdof:
        utils.run_cmd(cmd, err, stdout=stdof, stderr=stdof)
    # Check installation in develop mode
    with open(stdout, "r") as stdof:
        for line in stdof:
            if line.startswith("Location"):
                loc = line.split()[-1]
                assert glob.glob(os.path.join(loc, r'genomeAPCAT*egg-info'))
    os.remove(stdout)
    logfile = "install.log"
    content = ["Installing genomeAPCAT...",
               "Installing developer packages needed for genomeAPCAT",
               "Some dependencies needed for some subcommands of genomeAPCAT are "
               "not installed. Here is the list of missing dependencies, and for what they are "
               "used. If you plan to use the subcommands hereafter, first install required "
               "dependencies:",
               "- mmseqs (for pangenome subcommand)",
               "- mafft (to align persistent genomes in order to infer a phylogenetic tree "
               "after)",
               "- barrnap. If you use Prokka for functional annotation, it will not predict RNA.",
               "- prodigal : for annotate subcommand, you at least need prodigal (for syntaxic "
               "annotation only). If you even need functional annotation, also install prokka",
               "See more information on how to download/install those softwares in README or in "
               "documentation."]

    with open(logfile, "r") as logf:
        logf_content = "".join(logf.readlines())
        for linec in content:
            assert linec in logf_content

    # Check that needed packages are installed
    assert utils.is_package_installed("argparse")
    assert utils.is_package_installed("progressbar")
    assert utils.is_package_installed("numpy")
    assert utils.is_package_installed("matplotlib")
    assert utils.is_package_installed("Bio")
    os.remove(logfile)


def test_install_user():
    """
    Test that when installing from a computer containing only prokka, in user mode, it installs
    genomeAPCAT in /Users and returns list of dependencies
    """
    assert not utils.check_installed("barrnap")
    assert utils.check_installed("prokka")
    assert not utils.check_installed("genomeAPCAT")
    cmd = "python3 make --user"
    error = "Error trying to install genomeAPCAT from base"
    utils.run_cmd(cmd, error)
    assert not utils.check_installed("barrnap")
    assert utils.check_installed("prokka")
    assert utils.check_installed("genomeAPCAT")
    # Check logfile content
    logfile = "install.log"
    content = ["Installing genomeAPCAT in user mode...",
               "Some dependencies needed for some subcommands of genomeAPCAT are "
               "not installed. Here is the list of missing dependencies, and for what they are "
               "used. If you plan to use the subcommands hereafter, first install required "
               "dependencies:",
               "- mmseqs (for pangenome subcommand)",
               "- mafft (to align persistent genomes in order to infer a phylogenetic tree "
               "after)",
               "See more information on how to download/install those softwares in README or in "
               "documentation."]
    with open(logfile, "r") as logf:
        logf_content = "".join(logf.readlines())
        for linec in content:
            assert linec in logf_content
    # Check that needed packages are installed
    assert utils.is_package_installed("argparse")
    assert utils.is_package_installed("progressbar")
    assert utils.is_package_installed("numpy")
    assert utils.is_package_installed("matplotlib")
    assert utils.is_package_installed("Bio")

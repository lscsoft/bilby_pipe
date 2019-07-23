FROM continuumio/miniconda3

LABEL name="bilby_pipe Base miniconda3" \
maintainer="Gregory Ashton <gregory.ashton@ligo.org>" \
date="20190724"

RUN conda create -n env python=3.5
RUN echo "source activate env" > ~/.bashrc
ENV PATH /opt/conda/envs/env/bin:$PATH
RUN python --version

# Install conda-installable programs
RUN conda install -y matplotlib numpy scipy pandas astropy flake8
RUN conda install -c anaconda coverage configargparse future

# Install LALtools
RUN conda install -y -c conda-forge python-ldas-tools-framecpp
RUN conda install -y -c conda-forge python-nds2-client

# Install conda-forge-installable programs
RUN conda install -c conda-forge black ligo-gracedb gwpy lalsuite ligo.skymap bilby pesummary pytest-cov

# Install pip-requirements
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools pycondor>=0.5 coverage-badge


# MIDAS: Modularly Integrated Design Assistance Suite

<p align="center">
  <img src="https://github.com/ardorlab/MIDAS/assets/61293473/8114a773-988b-493a-9831-8d3f7b80408b" width="300" height="300">
</p>


Welcome to the Modularly Integrated Design Assistance Suite (MIDAS) repository. MIDAS utilizes inheritance, object-oriented, and functional programming to
create a simple, robust tool for solving optimization problems. It has been applied primarily to nuclear engineering design problems. MIDAS is an update on the previous version called MOF.


MIDAS is designed to provide users with a variety of optimization methodologies to solve opimization problems with a focus on nuclear engineering design problems. Containing multiple optimization methodologies in a single package allows for the reuse of code in multiple ways leading to a shorter, simpler, and more versatile optimization package.


Current optimization methodologies supported in MIDAS are:

* Genetic Algorithm
* Simulated Annealing
* Parallel Simulated Annealing
* Reinforcement Learning
  

# Code Installation

It is highly advised to install Miniconda or Anaconda. This will allow you to create a controlled Python environment where you can
install the required packages, especially if you want to use it in a cluster with limited permissions. Go to the 
site: https://docs.conda.io/en/latest/miniconda.html and download the latest Python 3 installer. The installer is a bash file with an example name "miniconda_install.sh". Now install conda and the 
required dependencies entering the following commands:

    bash miniconda_install.sh

    pip install pyyaml 

    conda install numpy

    conda install matplotlib 

	conda install pillow
	
	conda install h5py

    git clone https://github.com/ardorlab/MIDAS.git

If you want to use the newly added reinforcement learning algorithms, the python version in the environment should be 3.9 and some additional dependencies will need to be installed:

    pip3 install torch torchvision torchaudio

    pip install stable-baselines3[extra] 

An alternative way to configure the environment is to use the requirement files provided in the repository for pip and conda tools. This files are the "requirements_pip.txt" and "requirements_conda.txt".

Congratulations. The code is now installed in your local machine.

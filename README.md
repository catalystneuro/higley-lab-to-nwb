# higley-lab-to-nwb
NWB conversion scripts for Higley lab data to the [Neurodata Without Borders](https://nwb-overview.readthedocs.io/) data format.


## Installation
## Basic installation

You can install the latest release of the package with pip:

```
pip install higley-lab-to-nwb
```

We recommend that you install the package inside a [virtual environment](https://docs.python.org/3/tutorial/venv.html). A simple way of doing this is to use a [conda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/environments.html) from the `conda` package manager ([installation instructions](https://docs.conda.io/en/latest/miniconda.html)). Detailed instructions on how to use conda environments can be found in their [documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html).

### Running a specific conversion
Once you have installed the package with pip, you can run any of the conversion scripts in a notebook or a python file:

https://github.com/catalystneuro/higley-lab-to-nwb//tree/main/src/hadas_benisty_2022/hadas_benisty_2022_conversion_script.py




## Installation from Github
Another option is to install the package directly from Github. This option has the advantage that the source code can be modifed if you need to amend some of the code we originally provided to adapt to future experimental differences. To install the conversion from GitHub you will need to use `git` ([installation instructions](https://github.com/git-guides/install-git)). We also recommend the installation of `conda` ([installation instructions](https://docs.conda.io/en/latest/miniconda.html)) as it contains all the required machinery in a single and simple instal

From a terminal (note that conda should install one in your system) you can do the following:

```
git clone https://github.com/catalystneuro/higley-lab-to-nwb
cd higley-lab-to-nwb
conda env create --file make_env.yml
conda activate higley-lab-to-nwb-env
```

This creates a [conda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/environments.html) which isolates the conversion code from your system libraries.  We recommend that you run all your conversion related tasks and analysis from the created environment in order to minimize issues related to package dependencies.

Alternatively, if you want to avoid conda altogether (for example if you use another virtual environment tool) you can install the repository with the following commands using only pip:

```
git clone https://github.com/catalystneuro/higley-lab-to-nwb
cd higley-lab-to-nwb
pip install -e .
```

Note:
both of the methods above install the repository in [editable mode](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs).

### Running a specific conversion
To run a specific conversion, you might need to install first some conversion specific dependencies that are located in each conversion directory:
```
pip install -r src/higley_lab_to_nwb/hadas_benisty_2022/hadas_benisty_2022_requirements.txt
```

You can run a specific conversion with the following command:
```
python src/higley_lab_to_nwb/hadas_benisty_2022/hadas_benisty_2022_conversion_script.py
```

## Repository structure
Each conversion is organized in a directory of its own in the `src` directory:

    higley-lab-to-nwb/
    ├── LICENSE
    ├── make_env.yml
    ├── pyproject.toml
    ├── README.md
    ├── requirements.txt
    ├── setup.py
    └── src
        ├── higley_lab_to_nwb
        │   ├── conversion_directory_1
        │   └── hadas_benisty_2022
        │       ├── hadas_benisty_2022behaviorinterface.py
        │       ├── hadas_benisty_2022_convert_session.py
        │       ├── hadas_benisty_2022_metadata.yml
        │       ├── hadas_benisty_2022nwbconverter.py
        │       ├── hadas_benisty_2022_requirements.txt
        │       ├── hadas_benisty_2022_notes.md

        │       └── __init__.py
        │   ├── conversion_directory_b

        └── __init__.py

 For example, for the conversion `hadas_benisty_2022` you can find a directory located in `src/higley-lab-to-nwb/hadas_benisty_2022`. Inside each conversion directory you can find the following files:

* `hadas_benisty_2022_convert_sesion.py`: this script defines the function to convert one full session of the conversion.
* `hadas_benisty_2022_requirements.txt`: dependencies specific to this conversion.
* `hadas_benisty_2022_metadata.yml`: metadata in yaml format for this specific conversion.
* `hadas_benisty_2022behaviorinterface.py`: the behavior interface. Usually ad-hoc for each conversion.
* `hadas_benisty_2022nwbconverter.py`: the place where the `NWBConverter` class is defined.
* `hadas_benisty_2022_notes.md`: notes and comments concerning this specific conversion.

The directory might contain other files that are necessary for the conversion but those are the central ones.

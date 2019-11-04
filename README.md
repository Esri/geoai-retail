# GeoAI-Retail

_A GeoAI CookieCutter template for retail - a logical, reasonably standardized, but flexible project structure for performing and sharing retail geographic machine learning analysis work._

This cookiecutter template is designed to be used for GeoAI, geographic data science work utilizing ArcGIS Pro combined with Python machine learning technologies.

### Requirements to use the cookiecutter template:
-----------
 - ArcGIS Pro 3.4+ with the Business Analyst extension _and_ the Business Analyst data pack for the United States
 - Python 3.5+ with ArcPy (this is fulfilled by ArcGIS Pro)
 - [Cookiecutter](http://cookiecutter.readthedocs.org/en/latest/installation.html) >= 1.4.0: This can be installed with Conda:

``` cmd
> conda install -c conda-forge cookiecutter
```


### Getting Started
------------
First, use CookieCutter to create a new project according to this template.

``` cmd
> cookiecutter https://github.com/knu2xs/geoai-retail
```

Next, although not completely necessary, it is highly recommended to also create a Conda environment for performing analysis. For the `arcpy` bindings to work in the new environment you cannot simply create a new environment using the normal `conda create` command. Due to this, please run the `create_env.cmd` script. This will create a new environment with a few extra packages required for the workflows included in this template to work. Most notably, one of the required packages includes the companion project to this, [BA-Tools](https://github.com/knu2xs/ba-tools).

### Project Structure
------------

The directory structure of your new project will look like this: 

```
    ├── LICENSE
    ├── .env               <- Any environment variables here.
    ├── README.md          <- The top-level README for developers using this project.
    ├── environment.yml    <- Conda environment file.
    ├── create_env.cmd     <- Conda environment creation script.   
    │
    ├── arcgis             <- Root location for ArcGIS Pro project created as part of
    │                         data science project creation.
    │
    ├── scripts            <- Put scripts to run things here.
    |   │
    |   └── data           <- Scripts to download or generate data
    |       └── make_data.py
    |
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    |   │   └── interim.gdb<- Intermediate ArcGIS data that has been transformed.
    |   │
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    |       └── raw.gdb    <- Original, immutable data in ArcGIS formats - typically feature
    |                         classes. 
    │
    ├── docs               <- A default Sphinx project; see sphinx-doc.org for details
    │
    ├── models             <- Trained and serialized models, model predictions, or model summaries.          
    │   └── data_processing_tempate.ipynb
    │
    ├── notebooks          <- Jupyter notebooks. Naming convention is a 2 digits (for ordering),
    │                         descriptive name. e.g.: 01_exploratory_analysis.ipynb
    │
    ├── references         <- Data dictionaries, manuals, and all other explanatory materials.
    │
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting
    └── {{ cookiecutter.support_library }} <- Source code for use in this project.
```

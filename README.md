# GeoAI-Retail

GeoAI-Retail is a collection of resources combined into a succinct Python package streamlining the process of performing _Customer Centric Analysis_ using ArcGIS combined with Artificial Intelligence. This package dramatically streamlines the process of data munging to be able to build a model using Machine Learning or Deep Learning. Once created, the model can be used to perform inferencing to evaluate hypothetical scenarios of adding or removing locations. 

It is important to note, this package offers no opinion or guidance on creation of the model. Rather, it facilitates the process of data creation, tapping into the vast data and Geographic analysis capabilities of ArcGIS to automate much of  the feature engineering required prior to model training. Further, with this model created, this module enables inferencing using the created model to evaluate the effects of adding or removing a location from the store network.

## Analysis Workflow

GeoAI-Retail is a set of tools I created to facilitate retail analysis to accurately be able to quantitatively consider the complex interaction of geographic factors when attempting to predict performance of stores. Further, these tools also facilitate evaluating hypotheticals, the effect of adding or removing a location.

This type of analysis typically is performed using the idea of a trade area based on the assumption people within this trade area distance are those who are most likely will visit and patronize this location. This paradigm however, only takes into consideration one geographic factor, the distance potential customers are away from the store. 

This paradigm, when we attempted to tackle the more complex geographic interactions, proved inadequate and limiting. What happens when stores of the same brand are closer than this? What happens with a high density of competition is in the area? How does population density affect the trade area? What happens in high population density areas where driving no longer is the primary mode of transportation? What about areas of incredibly low population density, rural areas, where longer travel distances are considered normal? What about mixed population density areas where the trade area could encompass suburban, exurban and rural, where acceptable travel distances vary? What about the areas where the demographic is right, but the distance is longer, where the customers are willing to travel, but are excluded since falling outside of the defined trade area distance?

These are just a few of the confounding questions leading to a completely new method of for location analysis not by starting at the retail location, but rather starting at the customer location, and considering _all_ the factors (at least all we can think of) potentially affecting the customers' retail decision making process.

Modeling from the customers' perspective, from every single customer's individual perspective obviously does not scale. However, we can model at the block group level of geography since, at this level of geography, these areas are demographically homogeneous - everybody is the same. Therefore, the we we perform _customer centric analysis_ is from the perspective of these areas. This process starts with data preparation.

First, we simply need to know as much as possible about the people living in these origin areas, typically US Census Block Groups. With Esri's Business Analyst, we have access to just over 7,800 demographic variables. Hence, the first step is to create a table of these 7,800 variables we can relate back to these origin areas through a unique identifier.

Second we calculate the proximity from these customer origin areas to the closest retail locations for your brand. This is plural, your _locations_, we take into account not just the closest, but the second, third and fourth - up to the maximum number you decide is relevant. Next, we do the same thing for competitor locations, again up to the maximum number deemed relevant.

Third, we assemble the demographics and the proximity metrics into a single very large table with a single row for each origin area. This is the raw table we then can use to train a model.

## Current State

Currently, only analysis using __ArcGIS Pro__ with the __Business Analyst__ extension using __locally installed United States data__ is supported. If you dig into the package, you will find some functions supporting using REST services, but I have yet to get this workflow working reliably. Consequently, for now, it is dependent on ArcPy and locally installed resources in the United States. Depending on what use cases I run across, and have to support, international data and even full REST based analysis (not requiring ArcPy) may be supported in the future. Currently though, it is not.

## Getting Started

This project is an installable package using either `pip` or `conda`. Once installed, you will need to set up your store locations, competitor locations, and the geographic areas for your modeling and analysis. With this set up, you can begin training a model and finally inferencing.

### Installation

GeoAI-Retail is designed as an installable package so you can easily get up and running quickly. Please also make your life easier by using an isolated virtual environment for your analysis. Since ArcPy is a requirement, and this is tied to ArcGIS Pro, you will need to clone the default ArcGIS Pro Conda environment, `arcgispro-py3`.

Get started by cloning the default ArcGIS Pro environment. You can name it anything you like. In the example here, I am naming this environment `geoai_retail`, but you can name it anything you like. This will take a few minutes, so get comfortable.

`conda create --name geoai_retail --clone arcgispro-py3`

Next, switch to this new environment.

`activate geoai_retail`

Now, install the `geoai_retail` package!

`conda install geoai_retail`

### Data Setup

GeoAI Retail is a 

## Project Organization

```
    ├── LICENSE
	├── setup.py           <- Setup script for the library (geoai-retail)
    ├── README.md          <- The top-level README for developers using this project.
    │
    ├── arcgis             <- Root location for ArcGIS Pro project created as part of
    │                         data science project creation. This will not be here if
    │                         you do not have `arcpy` available.
    │
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    |   │   └── interim.gdb<- Intermediate ArcGIS data that has been transformed. This is
    |   │                     only generated if `arcpy` is available.
    |   │
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   |── raw            <- The original, immutable data dump.
    |       └── raw.gdb    <- Raw data unchanged and intended to be a starting point for analysis.
    │
    ├── docs               <- A default Sphinx project; see sphinx-doc.org for details
    │
    ├── models             <- Trained and serialized models, model predictions, or model summaries
    |
    ├── notebooks          <- Jupyter notebooks. Naming convention is a 2 digits (for ordering),
    │                         descriptive name. e.g.: 01_exploratory_analysis.ipynb
    │
    ├── references         <- Data dictionaries, manuals, and all other explanatory materials.
    │
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting
    │
    ├── environment.yml    <- The requirements file for reproducing the analysis environment. This 
    │                         is generated by running `conda env export > environment.yml` or
    │                         `make env_export`.                         
    │
    └── src                <- Source code for use in this project.
        │
        ├── data           <- Scripts to download or generate data
        │   └── make_dataset.py
        │
        └── geoai-retail <- Library to contain the bulk of code used in this project. 
							This is a module. 
```

<p><small>Project based on the <a target="_blank" href="https://github.com/knu2xs/cookiecutter-geoai">cookiecutter GeoAI project template</a>. This template, in turn, is simply an extension and light modification of the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>

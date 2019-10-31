# {{cookiecutter.project_name}}

{{cookiecutter.description}}

## Project Organization
------------

```
    ├── LICENSE
    ├── .env               <- Any environment variables here.
    ├── README.md          <- The top-level README for developers using this project.
    │
    ├── arcgis             <- Root location for ArcGIS Pro project created as part of
    │                         data science project creation. This will not be here if
    │                         you do not have `arcpy` available.
    │
    ├── scripts            <- Put scripts to run things here.
    |   │
    |   └── data           <- Scripts to download or generate data
    |       └── make_data.py
    |
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    |   │   └── interim.gdb<- Intermediate ArcGIS data that has been transformed. This is
    |   │                     only generated if `arcpy` is available.
    |   │
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    |       └── raw.gdb    <- Raw original, immutable data in ArcGIS formats, typically feature
    |                         classes. 
    │
    ├── docs               <- A default Sphinx project; see sphinx-doc.org for details
    │
    ├── models             <- Trained and serialized models, model predictions, or model summaries
    |   │                     
    │   └── data_processing_tempate.ipynb
    ├── notebooks          <- Jupyter notebooks. Naming convention is a 2 digits (for ordering),
    │                         descriptive name. e.g.: 01_exploratory_analysis.ipynb
    │
    ├── references         <- Data dictionaries, manuals, and all other explanatory materials.
    │
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting
    └── {{ cookiecutter.support_library }} <- Source code for use in this project.
```

<p><small>Project based on the <a target="_blank" href="https://github.com/knu2xs/cookiecutter-geoai">cookiecutter GeoAI project template</a>. This template, in turn, is simply an extension and light modification of the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>

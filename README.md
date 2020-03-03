# [GeoAI-Retail](https://esri.github.io/geoai-retail)

[GeoAI-Retail Project Homepage](https://esri.github.io/geoai-retail)

GeoAI-Retail is an [opinionated](https://medium.com/@stueccles/the-rise-of-opinionated-software-ca1ba0140d5b) analysis template striving to streamline and promote use of best practices for projects combining Geography and Artificial Intelligence for retail through a logical, reasonably standardized, and flexible project structure. A high level overview of the methods implemented in GeoAI-Retail is discussed in the [Customer-Centric Analysis StoryMap](https://storymaps.arcgis.com/stories/76006dd166294e6fae7e6164a1ff0a4a). 

GeoAI-Retail is an adaptation of GeoAI-Cookiecutter tailored for  retail analysis workflows. GeoAI-Cookiecutter grew out of a need within the Advanced Analytics team at Esri to streamline project bootstrapping, encourage innovation, increase repeatability, encourage documentation, and encourage best practices based on [strong opinions (best practices)](https://esri.github.io/geoai-retail#opinions). GeoAI-Retail implements these opinions with additional tight integration to the Esri Business Analyst extension capabilities heavily relying functionality from the [BA-Tools Python package](https://anaconda.org/knu2xs/ba-tools). This enables a data driven approach to model the relationship between who and where customers are, and customers' relationships to physical store locations using artificial intelligence. 

## Requirements to use the cookiecutter template:
 * ArcGIS Pro 2.4 or greater (Python 3.6 and Conda come with it)
 * [Cookiecutter](http://cookiecutter.readthedocs.org/en/latest/installation.html) >= 1.4.0

``` bash
> conda install -c conda-forge cookiecutter
```


## To start a new project, run:

``` bash
> cookiecutter https://GitHub.com/Esri/GeoAI-Retail
```

After answering a few questions, a new project will be created in your current directory. While you can get started from here, much of the functionality used by GeoAI-Retail takes advantage of a few other useful projects. Hence, please get these by creating a new environment and installing these dependencies. This process is streamlined for you using commands in the `make.bat` file.

``` bash
> cd <your-great-project-name>
> make env
```

From there you can get started working on setting up your data using the ArcGIS Pro project included in the `./arcgis` directory.

## Issues

Find a bug or want to request a new feature?  Please let us know by submitting an issue.

## Contributing

Esri welcomes contributions from anyone and everyone. Please see our [guidelines for contributing](https://github.com/esri/contributing).

## Licensing

Copyright 2020 Esri

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

A copy of the license is available in the repository's [LICENSE](LICENSE?raw=true) file.

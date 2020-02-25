# Environment Setup

The environment for running GeoAI-Retail must start with ArcGIS Pro with the Business Analyst Extension using local data. The Python environment installed with ArcGIS Pro is an instance of Conda, GeoAI-Retail extends the functionality through a few more capabilities available in this environment with additional packages. This involves creating a new environment and installing a few additional packages. Broadly, the steps to get up and running include the following.

* Install ArcGIS Pro with Business Analyst and local data
* Clone the ArcGIS Pro default environment, `arcgispro-py3`
* Install the `cookiecutter` package into the new environment
* Create a new project using the GeoAI-Retail template

## Clone the Default Environment

Python in ArcGIS Pro runs in a discrete Conda environment. This environment _should_ never be modified. Rather, a copy should be made, and modifications made to this copied environment. Further, if you are familiar with creating environments using an `environment.yml` file, this does not work due to the way the bindings work for accessing the functionality offered by ArcGIS Pro in Python through the `arcpy` module. Copying the default environment retains this functionality.

After installation, interacting with the Python Conda environment installed with ArcGIS Pro through the command line is accessed by going to Start > Programs > Python Command Prompt.

With the prompt open, to the left of the normal path in the command prompt, you will see the name of the Conda environment in parentheses. If you have not changed this, it will be `arcgispro-py3`. From this command prompt, you can begin by cloning the default Python environment using the following command. If following my convention, this new environment will be called `arcgis`.

```
> conda create --name arcgis --clone arcgispro-py3
```

Next, activate the environment to begin working in it.

```
> activate arcgis
```

Now, you will see this new environment name to the left of the command prompt in parenthesis.

> NOTE: If you want this available in _every_ command window, you can add Conda to your PATH environment variable. I typically do this when setting up a new machine by opening up a command prompt as administrator and using the following command.

```
> setx path "%PATH%;C:\Program Files\ArcGIS\Pro\bin\Python\Scripts"
```
 
## Install Cookiecutter

To use Cookiecutter templates, you first need to install Cookiecutter. This can be performed using the following command.

```
conda install -c conda-forge cookiecutter  
```

Once installed, you can now use Cookiecutter templates to start new projects, _including_ GeoAI-Retail.

## Try a New Project

From here, you are ready to start a new project, and get to work. Try this by switching to a directory where you can create a new folder, ensuring the environment is active where you installed Cookiecutter (`arcgis` if you followed my convention) and running the following command.

```
> cookiecutter https://github.com/knu2xs/geoai-cookiecutter
```

You will be asked to answer a few questions about your new project. For now, accepting the defaults will work for testing. Then, just to ensure everything is ready to start working, switch into the newly created directory, and try creating the Conda environment for your new project using the following command.

```
> make env
```

[This will create a Conda environment](../make/#gt-make-env) and install a few useful packages to get started working using GeoAI-Retail. If all of this works successfully, you are ready to dig in and start doing analysis using GeoAI-Retail!
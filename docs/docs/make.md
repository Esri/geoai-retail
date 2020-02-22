# Make - Using Make Commands

There is a _lot_ of functionality included in the GeoAI-Retail template. Instead of writing endless documentation detailing how to find and use all these resources, we have created a file, [`make.bat`](https://github.com/knu2xs/geoai-retail/blob/master/%7B%7Bcookiecutter.project_name%7D%7D/make.bat), containing shortcuts to accomplish a whole boatload of tasks. As with most all the functionality in this template, this came out of our own needs to streamline workflows, and not have to dig all around in the template to get boring and routing tasks accomplished. The commands available in `make.bat` fall into three general categories, data preprocessing, data management, and environment management.

## Data Preprocessing

More than anything else, GeoAI-Retail is a geographic feature engineering engine to create quantitative factors for use in machine learning modeling. GeoAI-Retail can then be used to revise the features and perform inferencing using the models created from the original data. Fortunately, for inferencing only a small amount of feature engineering needs to be performed. 

### `> make data`

The initial step of preparing the data for analysis can take a decent amoumnt of time. The heavy lifting is performed using a script, [`make_data.py`](https://github.com/knu2xs/geoai-retail/blob/master/%7B%7Bcookiecutter.project_name%7D%7D/scripts/make_data.py). While this script can be run directly, to make life easier, you can invoke the script directly using the command `make data`.

## Data Management

Although the code can be syncronized with version control, typically GitHub, datasets can be large, and frequently do not work well with version control. As a result, the data directory is excluded from version control in the `.gitignore` file, and can be saved to Azure Blob Storage.

### `> make get_data`

This is particuarly useful when collaborating on a project. After retrieving a project from version control, you can retrieve the data needed for the project using this command. The data will be downloaded from Azure Blob storage using credentials saved in the `.env` file and automatically extracted to the `./data` directory.

### `> make push_data`

This creates a zipped archive of the entire contents of the `./data` directory, and pushes it to Azure Blob storage using credentials saved in the `.env` file.

## Environment Management

Managing the Python Conda environment is dramatically streamlined using the commands contained in `make.bat`. Quite honestly, this is one of the single largest motivating factors for initially creating it.

### `> make env`

This is the most commonly used command. This command creates a Conda environment using the name set up when originally creating the project. Due to some nuances of how Conda is configured with ArcGIS Pro, you cannot simply create a new environment directly from the `environment.yml`. Rather, you have to clone the default ArcGIS Pro Conda environment `arcgispro-py3` and update the new environment using the `environment.yml` file. Additionally, if you like to use the mapping widget in Jupyter Lab, there are two additional steps. Hence, all of this is consolidated into one single step.

### `> make env_activate`

Sometimes the environment name is a little long, and sometimes you cannot recall what it is. Either way, it does not matter. This command will activate the project environment created using the command above, so you can get to work!

### `> make env_remove`

Multiple environments for projects quickly litter your computer. Hence, once finished with an environment for a project, this makes it easier to remove the environment from the machine.
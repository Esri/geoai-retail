CALL conda create --name {{cookiecutter.conda_environment_name}} --clone arcgispro-py3
CALL activate {{cookiecutter.conda_environment_name}}
CALL conda update -f environment.yml
jupyter labextension install @jupyter-widgets/jupyterlab-manager -y
jupyter labextension install arcgis-map-ipywidget@1.7.0 -y
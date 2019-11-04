call conda create --name {{cookiecutter.conda_environment_name}} --clone arcgispro-py3
call activate {{cookiecutter.conda_environment_name}}
call conda env update -f environment.yml
jupyter labextension install @jupyter-widgets/jupyterlab-manager -y
jupyter labextension install arcgis-map-ipywidget@1.7.0 -y
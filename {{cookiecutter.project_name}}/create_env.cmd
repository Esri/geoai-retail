CALL conda create --name {{cookiecutter.conda_environment_name}} --clone arcgispro-py3
CALL activate {{cookiecutter.conda_environment_name}}
CALL conda install -c esri arcgis -y
CALL conda install -c conda-forge nodejs scikit-learn python-dotenv -y
CALL conda install -c knu2xs ba-tools -y
jupyter labextension install @jupyter-widgets/jupyterlab-manager -y
jupyter labextension install arcgis-map-ipywidget@1.7.0 -y
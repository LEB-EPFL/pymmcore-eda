# pymmcore-eda
Smart microscopy library at LEB EPFL


## Installation using conda
1. From a conda terminal, create conda environment:
    ```
    conda create -n pymmcore-eda-env python<3.11
    ```
2. Activate the conda environment:
    ```
    conda activate pymmcore-eda-env
    ```
3. From within the environment, install pymmcore plus, pillow and mmcore:
    ```
    conda install conda-forge::pymmcore-plus
    conda install pillow
    mmcore install
    ```
4. Install Tensorflow and run inferences.
    Follow instructions from https://www.tensorflow.org/install/pip.
    E.g., for Windows:
    ```
    conda install -c conda-forge cudatoolkit=11.2 cudnn=8.1.0
    conda install 'tensorflow < 2.11'
    ```

    Once installed, you can run run_smart.py with instantianting the class Analyser::
    ```python
    analyser = Analyser(hub)
    # analyser = Dummy_Analyser(hub)
    ```

    **NOTE:** If tensorflow is not needed, you can run run_smart.py with instantianting the class Dummy_Analyser::
    ```python
    # analyser = Analyser(hub)
    analyser = Dummy_Analyser(hub)
    ```
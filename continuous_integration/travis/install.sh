# Install conda
case "$(uname -s)" in
    'Darwin')
        MINICONDA_FILENAME="Miniconda3-4.3.21-MacOSX-x86_64.sh"
        ;;
    'Linux')
        MINICONDA_FILENAME="Miniconda3-4.3.21-Linux-x86_64.sh"
        ;;
    *)  ;;
esac


wget https://repo.continuum.io/miniconda/$MINICONDA_FILENAME -O miniconda.sh
bash miniconda.sh -b -p $HOME/miniconda
export PATH="$HOME/miniconda/bin:$PATH"
conda config --set always_yes yes --set changeps1 no

# Create conda environment
conda create -q -n test-environment python=$PYTHON
source activate test-environment

# Pin matrix items
# Please see PR ( https://github.com/dask/dask/pull/2185 ) for details.
touch $CONDA_PREFIX/conda-meta/pinned
if ! [[ ${UPSTREAM_DEV} ]]; then
    echo "Pinning NumPy $NUMPY, pandas $PANDAS"
    echo "numpy $NUMPY" >> $CONDA_PREFIX/conda-meta/pinned
    echo "pandas $PANDAS" >> $CONDA_PREFIX/conda-meta/pinned
fi;

# Install dependencies.
conda install -q -c conda-forge \
    numpy \
    pandas \
    bcolz \
    blosc \
    bokeh \
    boto3 \
    chest \
    cloudpickle \
    coverage \
    cytoolz \
    distributed \
    graphviz \
    h5py \
    ipython \
    partd \
    psutil \
    "pytest<=3.1.1" \
    scikit-image \
    scikit-learn \
    scipy \
    sqlalchemy \
    toolz

if [[ ${UPSTREAM_DEV} ]]; then
    echo "Installing NumPy and Pandas dev"
    conda uninstall -y --force numpy pandas
    PRE_WHEELS="https://7933911d6844c6c53a7d-47bd50c35cd79bd838daf386af554a83.ssl.cf2.rackcdn.com"
    pip install -q --pre --no-deps --upgrade --timeout=60 -f $PRE_WHEELS numpy pandas
fi;

# install pytables from defaults for now
conda install -q pytables

pip install -q --upgrade --no-deps git+https://github.com/dask/partd
pip install -q --upgrade --no-deps git+https://github.com/dask/zict
pip install -q --upgrade --no-deps git+https://github.com/dask/distributed
pip install -q --upgrade --no-deps git+https://github.com/mrocklin/sparse
pip install -q --upgrade --no-deps git+https://github.com/dask/s3fs

if [[ $PYTHONOPTIMIZE != '2' ]] && [[ $NUMPY > '1.11.0' ]] && [[ $NUMPY < '1.13.0' ]]; then
    conda install -q -c conda-forge numba cython
    pip install -q --no-deps git+https://github.com/dask/fastparquet
fi

if [[ $PYTHON == '2.7' ]]; then
    pip install -q --no-deps backports.lzma mock
fi

pip install -q --upgrade --no-deps \
    cachey \
    graphviz \
    moto \
    pyarrow \
    pandas_datareader

pip install -q --upgrade \
    cityhash \
    flake8 \
    mmh3 \
    pytest-xdist \
    xxhash

# Install dask
pip install -q --no-deps -e .[complete]
echo conda list
conda list

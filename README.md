# Denon AVR integration for Remote Two

Using [denonavr](https://github.com/ol-iver/denonavr) and [uc-integration-api](https://github.com/aitatoi/integration-python-library)

The driver discovers Denon or Marantz AVRs on the network. A media player entity is exposed to the core.

Supported attributes:
- State (on, off, playing, paused, unknown)
- Title
- Album
- Artist
- Artwork
- Source

Supported commands:
- Turn on
- Turn off
- Next
- Previous
- Volume up
- Volume down
- Play/pause
- Source select

## Setup

```console
pip3 install -r requirements.txt
```

Manually install [ucapi](https://github.com/aitatoi/integration-python-library) library:
```console
pip3 install ../integration-python-library/dist/ucapi-$UCAPI_PYTHON_LIB_VERSION-py3-none-any.whl
```

## Code Style

- Code line length: 120
- Use double quotes as default (don't mix and match for simple quoting, checked with pylint).

Install tooling:
```console
pip3 install -r test-requirements.txt
```

### Verify
```console
python -m pylint *.py
python -m flake8 *.py --count --show-source --statistics
python -m isort *.py --check --verbose 
python -m black *.py --check --verbose --line-length 120
```

### Format Code
```console
python -m black *.py --line-length 120
```

### Sort Imports

```console
python -m isort *.py
```

## Build self-contained binary

After some tests, turns out python stuff on embedded is a nightmare. So we're better off creating a single binary file that has everything in it.

To do that, we need to compile it on the target architecture as `pyinstaller` does not support cross compilation.

The following can be used on x86 Linux:

```bash
sudo apt-get install qemu binfmt-support qemu-user-static
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
docker run --platform=aarch64 -v "$PWD:/io" -it ubuntu:focal

cd /io
apt-get update && apt-get install -y python3-pip
pip3 install pyinstaller -r requirements.txt
pyinstaller --clean --onefile driver.py
```

## Licenses

To generate the license overview file for remote-ui, [pip-licenses](https://pypi.org/project/pip-licenses/) is used
to extract the license information in JSON format. The output JSON is then transformed in a Markdown file with a
custom script.

Create a virtual environment for pip-licenses, since it operates on the packages installed with pip:
```console
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
```
Exit `venv` with `deactivate`.

Gather licenses:
```console
pip-licenses --python ./env/bin/python \
  --with-description --with-urls \
  --with-license-file --no-license-path \
  --with-notice-file \
  --format=json > licenses.json
```

Transform:
```console
cd tools
node transform-pip-licenses.js ../licenses.json licenses.md
```

# Denon AVR integration for Remote Two

Using [denonavr](https://github.com/ol-iver/denonavr)
and [uc-integration-api](https://github.com/aitatoi/integration-python-library)

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

```shell
pip3 install -r requirements.txt
```

## Code Style

- Code line length: 120
- Use double quotes as default (don't mix and match for simple quoting, checked with pylint).

Install tooling:

```shell
pip3 install -r test-requirements.txt
```

### Verify

The following tests are run as GitHub action for each push on the main branch and for pull requests.
They can also be run anytime on a local developer machine:

```shell
python -m pylint intg-denonavr
python -m flake8 intg-denonavr --count --show-source --statistics
python -m isort intg-denonavr/. --check --verbose 
python -m black intg-denonavr --check --verbose --line-length 120
```

Linting integration in PyCharm/IntelliJ IDEA:

1. Install plugin [Pylint](https://plugins.jetbrains.com/plugin/11084-pylint)
2. Open Pylint window and run a scan: `Check Module` or `Check Current File`

### Format Code

```shell
python -m black intg-denonavr --line-length 120
```

PyCharm/IntelliJ IDEA integration:

1. Go to `Preferences or Settings -> Tools -> Black`
2. Configure:

- Python interpreter
- Use Black formatter: `On code reformat` & optionally `On save`
- Arguments: `--line-length 120`

### Sort Imports

```shell
python -m isort intg-denonavr/.
```

## Build self-contained binary for Remote Two

After some tests, turns out python stuff on embedded is a nightmare. So we're better off creating a single binary file
that has everything in it.

To do that, we need to compile it on the target architecture as `pyinstaller` does not support cross compilation.

### x86-64 Linux

On x86-64 Linux we need Qemu to emulate the aarch64 target platform:

```bash
sudo apt install qemu binfmt-support qemu-user-static
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

Run pyinstaller:

```shell
docker run --rm --name builder \
    --platform=aarch64 \
    --user=$(id -u):$(id -g) \
    -v "$PWD":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11.6  \
    bash -c \
      "python -m pip install -r requirements.txt && \
      pyinstaller --clean --onefile --name intg-denonavr intg-denonavr/driver.py"
```

### aarch64 Linux / Mac

On an aarch64 host platform, the build image can be run directly (and much faster):

```shell
docker run --rm --name builder \
    --user=$(id -u):$(id -g) \
    -v "$PWD":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11.6  \
    bash -c \
      "python -m pip install -r requirements.txt && \
      pyinstaller --clean --onefile --name intg-denonavr intg-denonavr/driver.py"
```

## Licenses

To generate the license overview file for remote-ui, [pip-licenses](https://pypi.org/project/pip-licenses/) is used
to extract the license information in JSON format. The output JSON is then transformed in a Markdown file with a
custom script.

Create a virtual environment for pip-licenses, since it operates on the packages installed with pip:

```shell
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
```

Exit `venv` with `deactivate`.

Gather licenses:

```shell
pip-licenses --python ./env/bin/python \
  --with-description --with-urls \
  --with-license-file --no-license-path \
  --with-notice-file \
  --format=json > licenses.json
```

Transform:

```shell
cd tools
node transform-pip-licenses.js ../licenses.json licenses.md
```

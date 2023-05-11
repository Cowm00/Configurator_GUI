# Configurator GUI

This program is meant to help users easily configure and run CLI commands on their Cisco devices. It's a GUI program, that should be self explanatory. It's written to run tasks asynchronous and connect to multiple devices at the same time. There's no limit to the amount of devices you load into the program to run commands on. It will simply queue all devices and process them as fast as possible.

There are 4 tasks that can be run, either individually, mixed, or all at the same time.

The tasks are:
- Show/Check commands
- Global configurations
- Port configurations.
- Save configurations (write memory).

Help sections have been written to assist the user in understanding how to use the program. There are importable templates in the [Configuration Templates](https://github.com/Cowm00/Configurator_GUI/tree/master/Configuration%20Templates) directory. You just have to edit them and add the information you want to check or add the configurations you want to apply.

## Installation

In order to use the program, follow the instructions below. Dependencies are: :warning: **asyncssh** & **ttkbootstrap** :warning:

**Instructions:**

Clone the repo
```bash
git clone https://github.com/Cowm00/Configurator_GUI.git
```
Go to your project folder
```bash
cd Configurator_GUI
```

Set up a Python venv
First make sure that you have Python 3 installed on your machine. We will then be using venv to create an isolated environment with only the necessary packages.

Install virtualenv via pip
```bash
pip install virtualenv
```

Create the venv
```bash
python3 -m venv venv
```

Activate your venv
```bash
source venv/bin/activate
```

Install dependencies
```bash
pip install -r requirements.txt
```

Run the program
```bash
python App.py
```

## Author

2021-2023 Developed by [Rune Johannesen](https://github.com/cowm00)

## License

This code is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
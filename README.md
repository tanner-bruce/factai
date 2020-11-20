# FactAI

## Components

### FactAI Factorio Mod

The `factai_0.1.0` folder contains a mod for Factorio implementing various commands used for exporting data from Factorio. This piece will soon include executing commands against Factorio

### pyfactorio

A Python package consisting of a set of components for running Factorio, reading from the game state and visualizing the data with pygame.

## Running

### Prerequisites

- `poetry`, the Python package manager
- A copy of the `data` folder from Factorio inside a folder named `run` in this directory
- A save game file named `sb.zip` (or edit the code) in the `run` folder
- The `factai_0.1.0` mod installed in both this data directory and the regular install you will be using as the client. A symlink in each works well.

### Steps

- Inside `pyfactorio`, run `poetry install` and then `poetry shell`
- `cd ../` and then to run the UI and Factorio dedicated server: `python run.py`.
- The server will start on 127.0.0.1:34197, which you need to connect to form the client instance
- Once your player has joined the game the UI will start


## Inspiration & Thanks

- Factorio team, for making a great game
- A lot of code and ideas came from [github.com/deepmind/pysc2](https://github.com/deepmind/pysc2), with the base of this code essentially being a heavily modified fork of it
- The many various open source mods I looked at while
- François Perrad for the lua-MessagePack implementation
- The #mod-making discord channel
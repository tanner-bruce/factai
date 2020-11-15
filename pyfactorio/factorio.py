def run():
    print("run")

"""
show_features shows a feature map of everything visible to the current agent

features:
- enemies
- neutrals
- owned
- ore
- tiles
- buildings
- items on ground/belts
- logistic network zones
- pollution
- electrical grid
- turret coverage
"""
def show_features():
    print("run")

"""
reward calculates the reward score

positives:
- two main goals:
    - rockets launched
    - science per minute
- research completed
- item production statistics
    - bonus for science
- item consumption statistics
- number of enemies killed
- research completed

negatives:
- items in inventory
- number of enemies remaining
- time
"""
def reward():
    print("run")
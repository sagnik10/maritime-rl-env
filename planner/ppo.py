import numpy as np
import random

def policy_action(route):
    if len(route)<3:
        return route[-1]
    return route[random.randint(1,min(5,len(route)-1))]

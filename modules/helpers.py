import random
from itertools import product

def smart_param_generator(space, n_main_samples=10000, n_regressor_sets=3):
    """
    Генерує розумні комбінації на основі випадкового пошуку + стохастичного вибору регресорів.
    """

    # ---- 1. Підготовка простих параметрів ----
    simple_keys = [k for k in space if k != "regressors"]
    simple_space = [space[k] for k in simple_keys]

    # ---- 2. Пробіжка по основних параметрах ----
    for _ in range(n_main_samples):

        # випадковий вибір значень основних параметрів
        base = {
            k: random.choice(space[k])
            for k in simple_keys
        }

        # ---- 3. Варіанти регресорів ----
        reg_space = space["regressors"]
        reg_names = list(reg_space.keys())

        # 3.1. Варіант: без регресорів
        yield {**base, "regressors": {}}

        # 3.2. Стохастичні варіанти
        for _ in range(n_regressor_sets):

            chosen = {}

            for r in reg_names:
                if random.random() < 0.3:     # 30% шанс включити регресор
                    chosen[r] = random.choice(reg_space[r])

            yield {**base, "regressors": chosen}
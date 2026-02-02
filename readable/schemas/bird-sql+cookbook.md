```sql
-- Database: cookbook

-- Table: Ingredient (3346 rows)
CREATE TABLE Ingredient (
    ingredient_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    category TEXT NULL,
        -- <example>'dairy'</example>
    name TEXT NULL,
        -- <example>'1% lowfat cottage cheese'</example>
    plural TEXT NULL
        -- <values>{'#NAME?', 'es', 's'}</values>
);

-- Table: Nutrition (878 rows)
CREATE TABLE Nutrition (
    recipe_id INTEGER NULL PRIMARY KEY,
        -- <example>214</example>
        -- <fk> -> Recipe.recipe_id</fk>
    protein REAL NULL,
        -- <example>5.470</example>
    carbo REAL NULL,
        -- <example>41.290</example>
    alcohol REAL NULL,
        -- <example>0.000</example>
    total_fat REAL NULL,
        -- <example>11.530</example>
    sat_fat REAL NULL,
        -- <example>2.210</example>
    cholestrl REAL NULL,
        -- <example>1.390</example>
    sodium REAL NULL,
        -- <example>260.780</example>
    iron REAL NULL,
        -- <example>0.810</example>
    vitamin_c REAL NULL,
        -- <example>8.890</example>
    vitamin_a REAL NULL,
        -- <example>586.200</example>
    fiber REAL NULL,
        -- <example>0.870</example>
    pcnt_cal_carb REAL NULL,
        -- <example>56.800</example>
    pcnt_cal_fat REAL NULL,
        -- <example>35.680</example>
    pcnt_cal_prot REAL NULL,
        -- <example>7.530</example>
    calories REAL NULL,
        -- <example>290.790</example>
    FOREIGN KEY (recipe_id) REFERENCES Recipe(recipe_id)
);

-- Table: Quantity (5116 rows)
CREATE TABLE Quantity (
    quantity_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    recipe_id INTEGER NULL,
        -- <example>214</example>
        -- <fk> -> Recipe.recipe_id</fk>
        -- <fk> -> Nutrition.recipe_id</fk>
    ingredient_id INTEGER NULL,
        -- <example>1613</example>
        -- <fk> -> Ingredient.ingredient_id</fk>
    max_qty REAL NULL,
        -- <example>2.000</example>
    min_qty REAL NULL,
        -- <example>2.000</example>
    unit TEXT NULL,
        -- <example>'cup(s)'</example>
    preparation TEXT NULL,
        -- <example>'melted'</example>
    optional TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    FOREIGN KEY (recipe_id) REFERENCES Recipe(recipe_id),
    FOREIGN KEY (ingredient_id) REFERENCES Ingredient(ingredient_id),
    FOREIGN KEY (recipe_id) REFERENCES Nutrition(recipe_id)
);

-- Table: Recipe (1031 rows)
CREATE TABLE Recipe (
    recipe_id INTEGER NULL PRIMARY KEY,
        -- <example>214</example>
    title TEXT NULL,
        -- <example>'Raspberry Chiffon Pie'</example>
    subtitle TEXT NULL,
        -- <example>'with Banana Cream Whip'</example>
    servings INTEGER NULL,
        -- <example>10</example>
    yield_unit TEXT NULL,
        -- <example>'1 pie'</example>
    prep_min INTEGER NULL,
        -- <example>20</example>
    cook_min INTEGER NULL,
        -- <example>8</example>
    stnd_min INTEGER NULL,
        -- <example>305</example>
    source TEXT NULL,
        -- <example>'The California Tree Fruit Agreement'</example>
    intro TEXT NULL,
        -- <example>'Serve in stemmed glasses and top with sliced apricots for elegant endings.'</example>
    directions TEXT NULL
        -- <example>'For crust, preheat oven to 375 degrees F.
In light...ly slice remaining 2 plums and garnish top of pie.'</example>
);
```
```sql
-- Database: cookbook

/*
Table: Ingredient
Rows: 3346
Sample rows:
| ingredient_id   | category         | name                     | plural   |
|-----------------|------------------|--------------------------|----------|
| 1               | dairy            | 1% lowfat cottage cheese | [NULL]   |
| 6               | dairy            | 1% lowfat milk           | [NULL]   |
| 10              | Mexican products | 10-inch flour tortilla   | s        |
| 11              | cereals          | 100% bran cereal         | [NULL]   |
| 12              | dairy            | 2% lowfat milk           | [NULL]   |
| ...             | ...              | ...                      | ...      |
*/
CREATE TABLE Ingredient (
    ingredient_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    category TEXT NOT NULL,
        -- <example>'dairy'</example>
    name TEXT NOT NULL,
        -- <example>'1% lowfat cottage cheese'</example>
    plural TEXT NULL
        -- <values>{'#NAME?', 'es', 's'}</values>
);

/*
Table: Nutrition
Rows: 878
Sample rows:
| recipe_id   | protein   | carbo   | alcohol   | total_fat   | sat_fat   | cholestrl   | sodium   | iron   | vitamin_c   | vitamin_a   | fiber   | pcnt_cal_carb   | pcnt_cal_fat   | pcnt_cal_prot   | calories   |
|-------------|-----------|---------|-----------|-------------|-----------|-------------|----------|--------|-------------|-------------|---------|-----------------|----------------|-----------------|------------|
| 214         | 5.47      | 41.29   | 0.0       | 11.53       | 2.21      | 1.39        | 260.78   | 0.81   | 8.89        | 586.2       | 0.87    | 56.8            | 35.68          | 7.53            | 290.79     |
| 215         | 5.7       | 23.75   | 1.93      | 1.08        | 0.58      | 3.48        | 46.17    | 0.57   | 13.02       | 2738.24     | 0.62    | 67.38           | 6.89           | 16.17           | 141.01     |
| 216         | 4.9       | 26.88   | 0.0       | 1.1         | 0.58      | 3.46        | 41.79    | 0.37   | 6.13        | 1521.1      | 0.34    | 78.45           | 7.24           | 14.3            | 137.06     |
| 217         | 1.77      | 18.17   | 0.0       | 0.21        | 0.06      | 0.0         | 14.01    | 0.19   | 8.79        | 478.09      | 0.69    | 88.98           | 2.35           | 8.67            | 81.7       |
| 218         | 1.38      | 36.63   | 0.0       | 5.47        | 3.46      | 10.36       | 50.22    | 0.66   | 0.16        | 229.16      | 1.05    | 72.81           | 24.46          | 2.73            | 201.23     |
| ...         | ...       | ...     | ...       | ...         | ...       | ...         | ...      | ...    | ...         | ...         | ...     | ...             | ...            | ...             | ...        |
*/
CREATE TABLE Nutrition (
    recipe_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>214</example>
        -- <fk> -> Recipe.recipe_id</fk>
    protein REAL NOT NULL,
        -- <example>5.470</example>
    carbo REAL NOT NULL,
        -- <example>41.290</example>
    alcohol REAL NOT NULL,
        -- <example>0.000</example>
    total_fat REAL NOT NULL,
        -- <example>11.530</example>
    sat_fat REAL NOT NULL,
        -- <example>2.210</example>
    cholestrl REAL NOT NULL,
        -- <example>1.390</example>
    sodium REAL NOT NULL,
        -- <example>260.780</example>
    iron REAL NOT NULL,
        -- <example>0.810</example>
    vitamin_c REAL NOT NULL,
        -- <example>8.890</example>
    vitamin_a REAL NOT NULL,
        -- <example>586.200</example>
    fiber REAL NOT NULL,
        -- <example>0.870</example>
    pcnt_cal_carb REAL NOT NULL,
        -- <example>56.800</example>
    pcnt_cal_fat REAL NOT NULL,
        -- <example>35.680</example>
    pcnt_cal_prot REAL NOT NULL,
        -- <example>7.530</example>
    calories REAL NOT NULL,
        -- <example>290.790</example>
    FOREIGN KEY (recipe_id) REFERENCES Recipe(recipe_id)
);

/*
Table: Quantity
Rows: 5116
Sample rows:
| quantity_id   | recipe_id   | ingredient_id   | max_qty   | min_qty   | unit        | preparation   | optional   |
|---------------|-------------|-----------------|-----------|-----------|-------------|---------------|------------|
| 1             | 214         | 1613            | 2.0       | 2.0       | cup(s)      | [NULL]        | FALSE      |
| 2             | 214         | 3334            | 0.25      | 0.25      | cup(s)      | [NULL]        | FALSE      |
| 3             | 214         | 2222            | 0.5       | 0.5       | cup(s)      | melted        | FALSE      |
| 4             | 214         | 2797            | 0.25      | 0.25      | cup(s)      | or water      | FALSE      |
| 5             | 214         | 3567            | 3.0       | 3.0       | teaspoon(s) | [NULL]        | FALSE      |
| ...           | ...         | ...             | ...       | ...       | ...         | ...           | ...        |
*/
CREATE TABLE Quantity (
    quantity_id INTEGER NOT NULL PRIMARY KEY,
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

/*
Table: Recipe
Rows: 1031
Sample rows:
| recipe_id   | title                   | subtitle               | servings   | yield_unit   | prep_min   | cook_min   | stnd_min   | source                                           | intro                                                                                                     | directions                                                                                                                                                                                                  |
|-------------|-------------------------|------------------------|------------|--------------|------------|------------|------------|--------------------------------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 214         | Raspberry Chiffon Pie   | [NULL]                 | 10         | 1 pie        | 20         | 8          | 305        | The California Tree Fruit Agreement              | [NULL]                                                                                                    | For crust, preheat oven to 375 degrees F.
In lightly greased 10-inch pie plate, combine graham crack...into crust. Refrigerate 4 hours or overnight. Thinly slice remaining 2 plums and garnish top of pie.                                                                                                                                                                                                             |
| 215         | Apricot Yogurt Parfaits | [NULL]                 | 4          | [NULL]       | 5          | 2          | 65         | Produce for Better Health Foundation and 5 a Day | [NULL]                                                                                                    | Drain canned apricots, pour 1/4 cup of the juice into saucepan or microwave-safe dish. Sprinkle gela...ces or berries). Garnish each with a small spoonful of yogurt and sprinkling of brown sugar or mint. |
| 216         | Fresh Apricot Bavarian  | [NULL]                 | 8          | [NULL]       | 5          | 13         | 0          | The California Apricot Advisory Board            | Serve in stemmed glasses and top with sliced apricots for elegant endings.                                | Drop apricots into boiling water to cover. Return to boil and simmer for 5 minutes or until skins be...asses.

Note: One pound fresh apricots is 15 to 20. One and a half envelopes gelatin is 4 teaspoons.                                                                                                                                                                                                             |
| 217         | Fresh Peaches           | with Banana Cream Whip | 4          | [NULL]       | 10         | 0          | 0          | Produce for Better Health Foundation and 5 a Day | For a quick, low-cal dessert, serve this on other sliced fruit such as berries, instead of whipped cream. | In a small bowl, beat egg white until foamy. Add banana, sugar and lemon juice; beat until mixture f... 
Note: It is best to make this an hour or less before serving because it will darken upon standing.                                                                                                                                                                                                             |
| 218         | Canned Cherry Crisp     | [NULL]                 | 6          | [NULL]       | 10         | 5          | 0          | The Cherry Marketing Institute                   | Your microwave turns a can of cherry pie filling into a quick hot dessert.                                | Pour cherry pie filling into an 8-inch, round microwave-safe dish. Sprinkle with almond extract. Spr...ered, on HIGH (100% power) 4 to 5 minutes (rotating dish
twice), or until filling is hot and bubbly.                                                                                                                                                                                                             |
| ...         | ...                     | ...                    | ...        | ...          | ...        | ...        | ...        | ...                                              | ...                                                                                                       | ...                                                                                                                                                                                                         |
*/
CREATE TABLE Recipe (
    recipe_id INTEGER NOT NULL PRIMARY KEY,
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
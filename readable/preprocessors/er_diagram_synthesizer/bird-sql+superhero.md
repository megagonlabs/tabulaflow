```mermaid
erDiagram
    Superhero {
        table superhero "Core superhero profile including names, demographics, colours, race, publisher, alignment, height, and weight."
    }
    Gender {
        table gender "Lookup of gender values."
    }
    Alignment {
        table alignment "Lookup of alignment values."
    }
    Colour {
        table colour "Lookup of colour values."
    }
    Race {
        table race "Lookup of race values."
    }
    Publisher {
        table publisher "Lookup of publisher names."
    }
    Superpower {
        table superpower "Lookup of superpower names."
    }
    Attribute {
        table attribute "Lookup of attribute dimensions that are scored for each hero."
    }

    Superhero ||--o{ Gender : "HeroHasGender"
    %% Each superhero is assigned exactly one gender; each gender can apply to many superheroes.
    %% SQL join path: `FROM superhero JOIN gender ON superhero.gender_id = gender.id`

    Superhero |o--o{ Alignment : "HeroHasAlignment"
    %% A superhero may have one alignment; an alignment categorizes many superheroes.
    %% SQL join path: `FROM superhero JOIN alignment ON superhero.alignment_id = alignment.id`

    Superhero ||--o{ Colour : "HeroHasEyeColour"
    %% A superhero has one eye colour; a colour can be shared by many superheroes.
    %% SQL join path: `FROM superhero JOIN colour ON superhero.eye_colour_id = colour.id`

    Superhero ||--o{ Colour : "HeroHasHairColour"
    %% A superhero has one hair colour; a colour can be shared by many superheroes.
    %% SQL join path: `FROM superhero JOIN colour ON superhero.hair_colour_id = colour.id`

    Superhero ||--o{ Colour : "HeroHasSkinColour"
    %% A superhero has one skin colour; a colour can be shared by many superheroes.
    %% SQL join path: `FROM superhero JOIN colour ON superhero.skin_colour_id = colour.id`

    Superhero |o--o{ Race : "HeroHasRace"
    %% A superhero may have one race; each race can be associated with many superheroes.
    %% SQL join path: `FROM superhero JOIN race ON superhero.race_id = race.id`

    Superhero |o--o{ Publisher : "HeroPublishedByPublisher"
    %% A superhero may be associated with one publisher; a publisher can publish many superheroes.
    %% SQL join path: `FROM superhero JOIN publisher ON superhero.publisher_id = publisher.id`

    Superhero }o--o{ Superpower : "HeroHasSuperpower"
    %% Many-to-many association between superheroes and superpowers via hero_power.
    %% SQL join path: `FROM superhero JOIN hero_power ON superhero.id = hero_power.hero_id JOIN superpower ON hero_power.power_id = superpower.id`

    Superhero }o--o{ Attribute : "HeroHasAttributeScore"
    %% Many-to-many association between superheroes and attributes via hero_attribute; relationship carries attribute_value as the score.
    %% SQL join path: `FROM superhero JOIN hero_attribute ON superhero.id = hero_attribute.hero_id JOIN attribute ON hero_attribute.attribute_id = attribute.id`
```
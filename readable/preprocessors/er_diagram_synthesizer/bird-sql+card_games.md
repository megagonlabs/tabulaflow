```mermaid
erDiagram
    Card {
        table cards "One row per card printing in a set (core printed attributes, identifiers, and setCode)."
    }
    Set {
        table sets "One row per set/release product with size, codes, release date, and product metadata."
    }
    CardTranslation {
        table foreign_data "One row per (card uuid, language) with localized name/type/text/flavor; dependent on cards via uuid."
    }
    CardLegality {
        table legalities "One row per (card uuid, format) with the status value."
    }
    CardRuling {
        table rulings "One row per ruling entry (date, text) linked to a card by uuid."
    }
    SetTranslation {
        table set_translations "One row per (setCode, language) with the localized set name; dependent on sets via setCode."
    }

    Set }o--|| Card : "CardPrintedInSet"
    %% Each printed card belongs to exactly one set; a set contains many printed cards.
    %% SQL join path: `FROM cards JOIN sets ON cards.setCode = sets.code`

    Card }o--|| CardTranslation : "CardHasTranslations"
    %% A card can have multiple language-localized entries; each translation belongs to one card.
    %% SQL join path: `FROM cards JOIN foreign_data ON foreign_data.uuid = cards.uuid`

    Card }o--|| CardLegality : "CardHasLegality"
    %% A card may have zero or more legality rows across formats; each legality row refers to one card.
    %% SQL join path: `FROM cards JOIN legalities ON legalities.uuid = cards.uuid`

    Card }o--|| CardRuling : "CardHasRulings"
    %% A card may have zero or more rulings; each ruling is for one card.
    %% SQL join path: `FROM cards JOIN rulings ON rulings.uuid = cards.uuid`

    Set }o--|| SetTranslation : "SetHasTranslations"
    %% A set can have multiple localized names; each set translation references one set.
    %% SQL join path: `FROM sets JOIN set_translations ON set_translations.setCode = sets.code`

    Card }o--o{ Card : "CardOtherFaceLink"
    %% Some multi-face layouts link to other face records via non-enforced otherFaceIds; this is a self-relationship between cards.
    %% SQL join path: `FROM cards c1 JOIN cards c2 ON (',' || COALESCE(c1.otherFaceIds, '') || ',') LIKE '%,' || c2.uuid || ',%'`

    Set }o--o| Set : "SetHierarchy"
    %% Sets may reference a parent set (e.g., products grouped under a parent); this is a non-enforced self-relationship.
    %% SQL join path: `FROM sets child JOIN sets parent ON child.parentCode = parent.code`
```
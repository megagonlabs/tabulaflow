import streamlit as st
import asyncio
import argparse
import json
import os
import logging
from mintq.schema import NL2QDataset, SimpleNL2QTask, GoldQuery
from mintq.db_connector import SQLConnector
from mintq.formatters import SQLDefaultSchemaFormatter

# os.environ["MINTQ_CACHE_ENABLED"] = "0"


logger = logging.getLogger(__name__)


async def get_demo_dataset() -> NL2QDataset:
    tasks = [
        SimpleNL2QTask(
            qid="1",
            language="PostgresSQL",
            db="NOAA_GSOD",
            question="Retrieve the average temperature, average wind speed, and precipitation (null if incomplete) of station ID 725030 for each day from April 1 to 14, 2020?",
            gold_query=GoldQuery(
                query="""
SELECT "date", "temp" AS "avg_temp", "wdsp"::FLOAT AS "avg_wdsp", 
  CASE WHEN "flag_prcp" IN ('D', 'F', 'G') THEN "prcp" ELSE NULL END AS "prcp"
FROM NOAA_DATA.NOAA_GSOD.GSOD2020
WHERE "stn" = '725030'
  AND "date" BETWEEN DATE '2020-04-01' AND DATE '2020-04-14'
  AND "temp" != 9999.9 AND "wdsp" != '999.9' AND "prcp" != 99.99
ORDER BY "date";""".strip()
            ),
        ),
        SimpleNL2QTask(
            qid="2",
            language="PostgresSQL",
            db="NOAA_GSOD",
            question="Show all days with precipitation less than 0.1 inches.",
            gold_query=GoldQuery(
                query="""
SELECT stn, date, prcp, flag_prcp
FROM GSOD2020
WHERE prcp < 0.1 AND prcp <> 99.99
  AND flag_prcp NOT IN ('H','I');""".strip()
            ),
        ),
    ]
    import time

    t0 = time.time()
    db_connector = await SQLConnector.from_url_async(
        "demo+NOAA_GSOD",
        "NOAA_GSOD",
        "async",
        "postgresql+asyncpg://postgres:postgres@localhost:6432/weather",
    )
    print(f"Loaded db connector in {time.time() - t0:.2f} seconds.")
    return NL2QDataset(
        name="demo",
        split="dev",
        tasks=tasks,
        db_connectors={"NOAA_GSOD": db_connector},
    )


def get_ddl() -> list[str]:
    with open("demo_metadata/metadata/ddl.json", "r") as f:
        return json.load(f)["NOAA_DATA.NOAA_GSOD"]


def get_codebook() -> dict:
    with open("demo_metadata/metadata/code_book.json", "r") as f:
        return json.load(f)["NOAA_DATA.NOAA_GSOD"]


def get_side_effect() -> dict:
    with open("demo_metadata/metadata/side_effect.json", "r") as f:
        return json.load(f)["NOAA_DATA.NOAA_GSOD"]


async def database_browser(dataset: NL2QDataset):
    db = st.selectbox("Database", list(dataset.db_connectors.keys()))
    db_connector = dataset.db_connectors[db]
    schema = db_connector.schema
    formatter = SQLDefaultSchemaFormatter()

    ddl_tab, schema_tab, codebook_tab, side_effect_tab = st.tabs(["DDL", "Schema", "Codebook", "Side Effect"])
    with ddl_tab:
        ddls = get_ddl()
        st.text_area("DDL", "\n".join(ddls), height=600, label_visibility="collapsed")
    with schema_tab:
        st.text_area("Schema", formatter.format(schema), height=600, label_visibility="collapsed")
    with codebook_tab:
        codebooks = get_codebook()
        st.text_area("Codebook", json.dumps(codebooks, indent=2), height=600, label_visibility="collapsed")
    with side_effect_tab:
        side_effects = get_side_effect()
        st.text_area("Side Effect", json.dumps(side_effects, indent=2), height=600, label_visibility="collapsed")

async def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    logger.info(args)
    logger.info("")

    st.set_page_config(
        page_title="Megagon Metadata Demo",
        page_icon="📊",
        layout="wide",
    )
    st.markdown(
        """
        <style>
               .block-container {
                    padding-top: 3rem;
                    padding-bottom: 0rem;
                    padding-left: 2rem;
                    padding-right: 2rem;
                }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("📊 Megagon Metadata Demo")

    dataset = await get_demo_dataset()
    col1, col2 = st.columns([0.3, 0.7])
    with col1:
        await database_browser(dataset)

    # datalake_browser, = st.tabs(['datalake_browser'])


if __name__ == "__main__":
    asyncio.run(main())

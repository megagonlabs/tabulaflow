import jinja2
import litellm
import streamlit as st
import asyncio
import argparse
import json
import os
import logging
from mintq.schema import NL2QDataset, SimpleNL2QTask, GoldQuery
from mintq.db_connector import SQLConnector
from mintq.formatters import SQLBasicSchemaFormatter
from mintq.utils import extract_code

# os.environ["MINTQ_SCHEMA_CACHE_ENABLED"] = "0"


logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.WARNING)
logging.getLogger("mintq").setLevel(logging.INFO)


PROMPT = """
You are a database expert responsible for translating natural language questions into {{language}} queries.
- The query must follow the given database schema.
- You must follow the hints if provided.
- The final output should only include the SQL query, without explanation or any other text.
- Before returning the final output, always execute the query and check if the results match the question.
{% if language == "SnowflakeSQL" %}
- For Snowflake SQL, the column names must be quoted with double quotes (e.g. SELECT ORDER."product_id").
{% endif %}
{% if language == "PostgresSQL" %}
- When referencing tables, include the schema name if applicable. But do not include the database name.
{% endif %}

{% for key, value in metadata.items() %}
=== START OF {{ key.upper() }} ===
{{ value }}
=== END OF {{ key.upper() }} ===
{% endfor %}

Question to translate: {{question}}
{{language}} query:
""".strip()


async def get_demo_dataset() -> NL2QDataset:
    tasks = [
        SimpleNL2QTask(
            qid="1",
            language="PostgresSQL",
            db="NOAA_DATA",
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
            db="NOAA_DATA",
            question="Show all days with precipitation less than 0.1 inches.",
            gold_query=GoldQuery(
                query="""
SELECT stn, date, prcp, flag_prcp
FROM GSOD2020
WHERE prcp < 0.1 AND prcp <> 99.99
  AND flag_prcp NOT IN ('H','I');""".strip()
            ),
        ),
        SimpleNL2QTask(
            qid="3",
            language="PostgresSQL",
            db="NOAA_DATA",
            question="List all days where snow depth was reported (sndp not missing) but snow/ice pellets event was 0.",
            gold_query=GoldQuery(
                query="""
SELECT stn, date, sndp
FROM GSOD2020
WHERE sndp <> 999.9
  AND snow_ice_pellets = '0';""".strip()
            ),
        ),
        SimpleNL2QTask(
            qid="4",
            language="PostgresSQL",
            db="NOAA_DATA",
            question="Count, for each station, the number of wet days in 2020.",
            gold_query=GoldQuery(
                query="""
SELECT stn, 
       COUNT(*) AS wet_days
FROM GSOD2020
WHERE year = '2020'
  AND (rain_drizzle = '1' OR snow_ice_pellets = '1' OR hail = '1')
GROUP BY stn;
""".strip()
            ),
        ),
        SimpleNL2QTask(
            qid="5",
            language="PostgresSQL",
            db="NOAA_DATA",
            question="Find stations that rarely snow.",
            gold_query=GoldQuery(
                query="""
SELECT DISTINCT stn
FROM GSOD2020
WHERE stn IN (
    SELECT stn
    FROM GSOD2020
    WHERE snow_ice_pellets = '1'
    GROUP BY stn, mo
    HAVING COUNT(*) < 2
);
""".strip()
            ),
        ),
        SimpleNL2QTask(
            qid="6",
            language="PostgresSQL",
            db="NOAA_DATA",
            question="Return the top 5 stations with the highest number of wet days in 2020. ",
            gold_query=GoldQuery(
                query="""
SELECT stn, SUM(wet_day_flag) AS wet_days
FROM GSOD2020
WHERE year = '2020'
GROUP BY stn
ORDER BY wet_days DESC
LIMIT 5;
""".strip()
            ),
        ),
        SimpleNL2QTask(
            qid="7",
            language="PostgresSQL",
            db="NOAA_DATA",
            question="Return all dates with extreme events with precipitation.",
            gold_query=GoldQuery(
                query="""
SELECT date
FROM GSOD2020
WHERE prcp > monthly_avg_temp
  AND extreme_event_flag = '1'
""".strip()
            ),
        ),
    ]
    import time

    t0 = time.time()
    db_connector = await SQLConnector.from_url_async(
        "demo+NOAA_DATA",
        "NOAA_DATA",
        "async",
        "postgresql+asyncpg://postgres:postgres@localhost:6432/weather",
    )
    db_connector.schema.name = "weather"
    db_connector.schema.tables = [t for t in db_connector.schema.tables if t.name != "gsod2020_orig"]
    print(f"Loaded db connector in {time.time() - t0:.2f} seconds.")
    return NL2QDataset(
        name="demo",
        split="dev",
        tasks=tasks,
        db_connectors={"NOAA_DATA": db_connector},
    )


def get_ddl() -> str:
    with open("demo_metadata/metadata/ddl.json", "r") as f:
        return "\n".join(json.load(f)["NOAA_DATA.noaa_gsod"])


def get_codebook() -> str:
    with open("demo_metadata/metadata/code_book.json", "r") as f:
        d = json.load(f)["NOAA_DATA.noaa_gsod"]
        d = {k.replace("NOAA_DATA.", ""): v for k, v in d.items()}
        return json.dumps(d, indent=2)


def get_side_effect() -> str:
    with open("demo_metadata/metadata/side_effect.json", "r") as f:
        d = json.load(f)["NOAA_DATA.noaa_gsod"]
        d = {k.replace("NOAA_DATA.", ""): v for k, v in d.items()}
        return json.dumps(d, indent=2)


def get_hints() -> str:
    with open("demo_metadata/metadata/hints.json", "r") as f:
        return "\n".join([f"- {hint}" for hint in json.load(f)])

def get_column_desc() -> str:
    with open("demo_metadata/metadata/column_desc_stripped.json", "r") as f:
        d = json.load(f)["NOAA_DATA.noaa_gsod"]
        d = {k.replace("NOAA_DATA.", ""): v for k, v in d.items()}
        return json.dumps(d, indent=2)


def get_metadata(schema: str) -> dict[str, str]:
    return {
        "DDL": get_ddl(),
        "Schema+": schema,
        "Codebook": get_codebook(),
        "Semantic Dependency": get_side_effect(),
        "Hints": get_hints(),
        "Column Desc": get_column_desc(),
    }


async def run_simple_zero_shot(
    question: str,
    db_connector: SQLConnector,
    metadata: dict[str, str],
    llm: str,
    temperature: float,
    language="PostgresSQL",
    key="run_left",
) -> str:
    prompt = jinja2.Template(PROMPT).render(question=question, metadata=metadata, language=language)
    logger.info(prompt)
    with st.chat_message("human", avatar="human"):
        st.write(question)

    # with st.container(height=600, border=False):
    #     st.text_area("Prompt", prompt, height="stretch", label_visibility="collapsed")
    with st.spinner("Running LLM..."):
        response = await litellm.acompletion(
            model=llm, messages=[{"role": "user", "content": prompt}], temperature=temperature
        )
    query = response["choices"][0]["message"]["content"]
    query = extract_code(query)
    logger.info(query)
    with st.chat_message("assistant", avatar="assistant"):
        st.code(query, language="sql")
    with st.spinner("Querying database..."):
        exec_result = await db_connector.run_query_async(query)
    df = exec_result.df
    
    with st.chat_message("assistant", avatar=":material/database:"):
        if df is not None:
            st.dataframe(df)
            if exec_result.df_is_truncated:
                st.warning(f"Table truncated to {len(df)} rows.")
        else:
            st.error(exec_result.error)

    st.session_state[key] = {
        "prompt": question,
        "query": query,
        "exec_result": exec_result,
    }


async def database_browser(
    dataset: NL2QDataset, metadata: dict[str, str]
) -> tuple[SimpleNL2QTask, SQLConnector, str, float]:
    with st.container(border=True):
        col1, col2 = st.columns([0.3, 0.7])
        with col1:
            db = st.selectbox("Database", list(dataset.db_connectors.keys()))
        with col2:
            question = st.selectbox("Question", [task.question for task in dataset.tasks], index=1)
        col1, col2 = st.columns([0.45, 0.55])
        with col1:
            llm = st.selectbox("LLM", ["openai/gpt-4.1", "openai/gpt-5", "openai/gpt-4o-mini", "openai/gpt-4o", ], index=0)
        with col2:
            if llm == "openai/gpt-5":
                temperature = st.slider(
                    "Temperature", min_value=0.0, max_value=2.0, value=1.0, step=0.01, disabled=True
                )
            else:
                temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=0.0, step=0.01)

    db_connector = dataset.db_connectors[db]

    tabs = st.tabs(list(metadata.keys()))
    for tab, (key, value) in zip(tabs, metadata.items()):
        with tab:
            with st.container(height=450, border=False):
                st.text_area(key, value, height="stretch", label_visibility="collapsed")
    task = next(task for task in dataset.tasks if task.question == question)
    return task, db_connector, llm, temperature


async def text2sql_panel(
    task: SimpleNL2QTask, db_connector: SQLConnector, metadata: dict[str, str], llm: str, temperature: float
):
    # c1, c2, c3 = st.columns([0.5, 0.3, 0.2])
    # with c2:
    #     selected_question = st.selectbox(
    #         "Question", [task.question for task in dataset.tasks], label_visibility="collapsed"
    #     )
    # with c1:
    #     with st.container(height=98, border=False):
    #         question = st.text_area("Question", selected_question, height="stretch", label_visibility="collapsed")
    # with c2:
    #     run = st.button("Run")
    with st.container(height=68, border=False):
        question = st.text_area("Question", task.question, height="stretch", label_visibility="collapsed")

    left, right = st.columns([0.5, 0.5], gap="medium")
    with left:
        left_c1, left_c2 = st.columns([0.7, 0.3])
        with left_c1:
            meta_types_left = st.pills(
                "metadata",
                list(metadata.keys()),
                default=["DDL"],
                selection_mode="multi",
                label_visibility="collapsed",
                key="metadata_1",
            )
        with left_c2:
            with st.container(horizontal_alignment="right"):
                run_left = st.button("Run", key="run_left")
    with right:
        right_c1, right_c2 = st.columns([0.7, 0.3])
        with right_c1:
            meta_types_right = st.pills(
                "metadata",
                list(metadata.keys()),
                default=list(metadata.keys())[1:],
                selection_mode="multi",
                label_visibility="collapsed",
                key="metadata_2",
            )
        with right_c2:
            with st.container(horizontal_alignment="right"):
                run_right = st.button("Run", key="run_right")

    if not run_left:
        with left:
            if "run_left_result" in st.session_state:
                with st.chat_message("human", avatar="human"):
                    st.write(st.session_state["run_left_result"]["prompt"])
                with st.chat_message("assistant", avatar="assistant"):
                    st.code(st.session_state["run_left_result"]["query"], language="sql")
                with st.chat_message("assistant", avatar=":material/database:"):
                    exec_result = st.session_state["run_left_result"]["exec_result"]
                    if exec_result.df is not None:
                        st.dataframe(exec_result.df)
                        if exec_result.df_is_truncated:
                            st.warning(f"Table truncated to {len(exec_result.df)} rows.")
                    else:
                        st.error(exec_result.error)

    if not run_right:
        with right:
            if "run_right_result" in st.session_state:
                with st.chat_message("human", avatar="human"):
                    st.write(st.session_state["run_right_result"]["prompt"])
                with st.chat_message("assistant", avatar="assistant"):
                    st.code(st.session_state["run_right_result"]["query"], language="sql")
                with st.chat_message("assistant", avatar=":material/database:"):
                    exec_result = st.session_state["run_right_result"]["exec_result"]
                    if exec_result.df is not None:
                        st.dataframe(exec_result.df)
                        if exec_result.df_is_truncated:
                            st.warning(f"Table truncated to {len(exec_result.df)} rows.")
                    else:
                        st.error(exec_result.error)

    if run_left:
        with left:
            metadata_selected = {k: metadata[k] for k in meta_types_left}
            await run_simple_zero_shot(
                question,
                db_connector,
                metadata_selected,
                llm,
                temperature,
                language="PostgresSQL",
                key="run_left_result",
            )

    if run_right:
        with right:
            metadata_selected = {k: metadata[k] for k in meta_types_right}
            await run_simple_zero_shot(
                question,
                db_connector,
                metadata_selected,
                llm,
                temperature,
                language="PostgresSQL",
                key="run_right_result",
            )


async def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    logger.info(args)
    logger.info("")

    st.set_page_config(
        page_title="NL2SQL Metadata Demo",
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

    col1, col2 = st.columns([0.3, 0.7])
    with col1:
        st.title("📊 NL2SQL Metadata Demo")
    dataset = await get_demo_dataset()
    metadata = get_metadata(SQLBasicSchemaFormatter().format(dataset.db_connectors["NOAA_DATA"].schema))
    with col1:
        task, db_connector, llm, temperature = await database_browser(dataset, metadata)
    with col2:
        await text2sql_panel(task, db_connector, metadata, llm, temperature)

    # datalake_browser, = st.tabs(['datalake_browser'])


if __name__ == "__main__":
    asyncio.run(main())

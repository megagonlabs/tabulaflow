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
from mintq.formatters import SQLDefaultSchemaFormatter
from mintq.utils import extract_code

# os.environ["MINTQ_CACHE_ENABLED"] = "0"


logger = logging.getLogger(__name__)


PROMPT = """
You are a database expert responsible for translating natural language questions into {{language}} queries.
- The query must follow the given database schema.
- You must follow the hints if provided.
- The final output should not include additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, the final query should not fetch the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, the final query should not fetch the score.
  - If the question asks for the list of objects (e.g. students), fetch the IDs of the objects.
- The final output should only include the SQL query, without explanation or any other text.
- Before returning the final output, always execute the query and check if the results match the question.
{% if language == "SnowflakeSQL" %}
- For Snowflake SQL, the column names must be quoted with double quotes (e.g. SELECT ORDER."product_id").
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
    ]
    import time

    t0 = time.time()
    db_connector = await SQLConnector.from_url_async(
        "demo+NOAA_DATA",
        "NOAA_DATA",
        "async",
        "postgresql+asyncpg://postgres:postgres@localhost:6432/weather",
    )
    print(f"Loaded db connector in {time.time() - t0:.2f} seconds.")
    return NL2QDataset(
        name="demo",
        split="dev",
        tasks=tasks,
        db_connectors={"NOAA_DATA": db_connector},
    )


def get_ddl() -> list[str]:
    with open("demo_metadata/metadata/ddl.json", "r") as f:
        return json.load(f)["NOAA_DATA.noaa_gsod"]


def get_codebook() -> dict:
    with open("demo_metadata/metadata/code_book.json", "r") as f:
        return json.load(f)["NOAA_DATA.noaa_gsod"]


def get_side_effect() -> dict:
    with open("demo_metadata/metadata/side_effect.json", "r") as f:
        return json.load(f)["NOAA_DATA.noaa_gsod"]


def get_metadata() -> dict[str, str]:
    return {
        "ddl": get_ddl(),
        "codebook": get_codebook(),
        "side effect": get_side_effect(),
    }


async def run_simple_zero_shot(
    question: str, db_connector: SQLConnector, metadata: dict[str, str], llm="openai/gpt-4o", language="PostgresSQL",
    key="run_left",
) -> str:
    prompt = jinja2.Template(PROMPT).render(question=question, metadata=metadata, language=language)
    with st.chat_message("human", avatar="human"):
        st.write(question)

    # with st.container(height=600, border=False):
    #     st.text_area("Prompt", prompt, height="stretch", label_visibility="collapsed")
    with st.spinner("Running LLM..."):
        response = await litellm.acompletion(model=llm, messages=[{"role": "user", "content": prompt}], temperature=0.0)
    query = response["choices"][0]["message"]["content"]
    query = extract_code(query)
    with st.chat_message("assistant", avatar="assistant"):
        st.code(query, language="sql")
    with st.spinner("Querying database..."):
        exec_result = await db_connector.run_query_async(query)
    df = exec_result.df
    with st.chat_message("assistant", avatar=":material/database:"):
        if df is not None:
            st.dataframe(df)
        else:
            st.error(exec_result.error)

    st.session_state[key] = {
        "prompt": question,
        "query": query,
        "exec_result": exec_result,
    }


async def database_browser(dataset: NL2QDataset) -> tuple[SimpleNL2QTask, SQLConnector]:
    db = st.selectbox("Database", list(dataset.db_connectors.keys()))
    question = st.selectbox("Question", [task.question for task in dataset.tasks])

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

    task = next(task for task in dataset.tasks if task.question == question)
    return task, db_connector


async def text2sql_panel(task: SimpleNL2QTask, db_connector: SQLConnector, metadata: dict[str, str]):
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

    left, right = st.columns([0.5, 0.5])
    with left:
        left_c1, left_c2 = st.columns([0.7, 0.3])
        with left_c1:
            meta_types_left = st.pills(
                "metadata",
                ["DDL", "Schema", "Codebook", "Side Effect"],
                default=["DDL"],
                selection_mode="multi",
                label_visibility="collapsed",
                key="metadata_1",
            )
        with left_c2:
            run_left = st.button("Run", key="run_left")
    with right:
        right_c1, right_c2 = st.columns([0.7, 0.3])
        with right_c1:
            meta_types_right = st.pills(
                "metadata",
                ["DDL", "Schema", "Codebook", "Side Effect"],
            default=["Schema", "Codebook", "Side Effect"],
                selection_mode="multi",
                label_visibility="collapsed",
                key="metadata_2",
            )
        with right_c2:
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
                    else:
                        st.error(exec_result.error)

    if not run_left and not run_right:
        st.stop()

    meta_types_left = [v.lower() for v in meta_types_left]
    meta_types_right = [v.lower() for v in meta_types_right]
    if run_left:
        with left:
            metadata_selected = {k: v for k, v in metadata.items() if k.lower() in meta_types_left}
            await run_simple_zero_shot(
                task.question, db_connector, metadata_selected, llm="openai/gpt-4o", language="PostgresSQL", key="run_left_result"
            )
    
    if run_right:
        with right:
            metadata_selected = {k: v for k, v in metadata.items() if k.lower() in meta_types_right}
            await run_simple_zero_shot(
                task.question, db_connector, metadata_selected, llm="openai/gpt-4o", language="PostgresSQL", key="run_right_result"
            )


async def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    logger.info(args)
    logger.info("")

    st.set_page_config(
        page_title="Text-to-SQL Metadata Demo",
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
        st.title("📊 Text-to-SQL Metadata Demo")
    dataset = await get_demo_dataset()
    metadata = get_metadata()
    formatter = SQLDefaultSchemaFormatter()
    metadata["schema"] = formatter.format(dataset.db_connectors["NOAA_DATA"].schema)
    with col1:
        task, db_connector = await database_browser(dataset)
    with col2:
        await text2sql_panel(task, db_connector, metadata)

    # datalake_browser, = st.tabs(['datalake_browser'])


if __name__ == "__main__":
    asyncio.run(main())

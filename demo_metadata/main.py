import streamlit as st
import argparse
import os
import logging


logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongodb_url", default=f"mongodb://{os.environ.get('DB_HOST')}:27017")
    parser.add_argument("--neo4j_url", default=f"bolt://{os.environ.get('DB_HOST')}:7687")
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

    # datalake_browser, = st.tabs(['datalake_browser'])


if __name__ == "__main__":
    main()

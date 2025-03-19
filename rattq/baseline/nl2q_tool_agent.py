import argparse
import os
import shutil
import json
from tqdm import trange
from litellm import batch_completion
from smolagents import ToolCallingAgent, LiteLLMModel, CodeAgent
from concurrent.futures import ThreadPoolExecutor
from rattq.utils import get_db_connectors, load_nl2q_samples, parse_query


NL2Q_PROMPT = """
Translate the following natural language question into a {language} query.
- The query must follow the database schema.
- You must use the hints to generate the query.
- The final answer must be the query rather than the result of the query.
- Do not include additional columns that are not required by the question.
  - For example, if the question only ask for the highest score but not the name of the student, do not fetch the name of the student.
  - Similarly, if the question only ask for the student with the highest score but not the score, do not fetch the score.
- The observation being empty indicates that the query is incorrect, try a different query.
- Before submitting the final query as answer, always execute the query to validate it.
  - The execution result should be non-empty and reasonable (not null, not zero, etc.)

Database Schema:
{schema}

Question: {question}

Hints:
{evidence}

Query:
""".strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--llm', default='openai/gpt-4o')
    parser.add_argument('--prompt', default='default', choices=['default'])
    parser.add_argument('--dataset', default='bird-sql')
    parser.add_argument('--batch_size', default=50, type=int)
    parser.add_argument('--wait_time_between_batches', default=0.0, type=float)
    parser.add_argument('--result_dir', default='output/nl2q_tool_agent_gpt-4o/')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    if args.debug:
        parser.set_defaults(batch_size=1, overwrite=True, result_dir='output/test/')
    args = parser.parse_args()
    print(args)
    print()

    if os.path.exists(args.result_dir):
        if not args.overwrite:
            print(f'{args.result_dir} already exists. Use --overwrite to overwrite the directory.')
            return
        else:
            shutil.rmtree(args.result_dir)
    os.makedirs(args.result_dir)

    db_connectors = get_db_connectors(args.dataset, splits=['dev'])
    print(f'Loaded {len(db_connectors)} databases from {args.dataset} dev set.')

    dev_samples = load_nl2q_samples(args.dataset, 'dev')
    print(f'Loaded {len(dev_samples)} samples from {args.dataset} dev set.')

    if args.debug:
        dev_samples = [sample for sample in dev_samples
                       if sample.qid in ('bird-sql_dev_1', 'bird-sql_dev_2', 'bird-sql_dev_10',
                                         'bird-sql_dev_15', 'bird-sql_dev_16')]

    model = LiteLLMModel(model_id=args.llm)

    res = []
    for i in trange(0, len(dev_samples), args.batch_size):
        j = min(i + args.batch_size, len(dev_samples))
        batch_samples = dev_samples[i:j]
        prompts = [
            NL2Q_PROMPT.format(
                language=sample.language,
                schema=db_connectors[sample.db].get_schema(),
                evidence=sample.evidence,
                question=sample.question
            ) for sample in batch_samples
        ]
        if i == 0:
            print(f'<prompts>{prompts[0]}</prompts>')

        responses = []
        tools = [db_connectors[sample.db].as_smolagent_tool() for sample in batch_samples]
        agents = [ToolCallingAgent(tools=[tool], model=model) for tool in tools]

        with ThreadPoolExecutor(max_workers=len(prompts)) as executor:
            futures = [executor.submit(agent.run, prompt) for agent, prompt in zip(agents, prompts)]
            responses = [future.result() for future in futures]

        if i == 0:
            print(f'<last_agent_step_input>{agents[-1].memory.steps[-1].model_input_messages}</last_agent_step_input>')
            print(f'<last_agent_step_output>{agents[-1].memory.steps[-1].model_output_message}</last_agent_step_output>')
            print(f'<response>{responses[0]}</response>')

        for item, r in zip(batch_samples, responses):
            item.pred_query = parse_query(r)
            res.append(item)
        
    output_path = os.path.join(args.result_dir, f'result.json')
    with open(output_path, 'w') as fout:
        json.dump([item.model_dump(mode='json') for item in res], fout, indent=2)
    print(f'Saved result to {output_path}')


if __name__ == '__main__':
    main()

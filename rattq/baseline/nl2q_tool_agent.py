import argparse
import os
import shutil
import json
from tqdm import trange
from litellm import batch_completion
from smolagents import ToolCallingAgent, LiteLLMModel, CodeAgent
from rattq.baseline.data_utils import get_db_connectors, load_nl2q_samples


NL2Q_PROMPT = """
Translate the following natural language question into a {language} query.
- Output the query only, without any additional explanation.
- Always execute the query before submitting the final query as answer.


Database Schema:
{schema}

Extra Evidence:
{evidence}

Question: {question}

Query:
""".strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--llm', default='openai/gpt-4o')
    parser.add_argument('--prompt', default='default', choices=['default'])
    parser.add_argument('--dataset', default='bird-sql')
    parser.add_argument('--batch_size', default=10, type=int)
    parser.add_argument('--wait_time_between_batches', default=0.0, type=float)
    parser.add_argument('--result_dir', default='output/nl2q_tool_agent_gpt-4o/')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--debug', action='store_true')
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
        dev_samples = dev_samples[:3]

    model = LiteLLMModel(model_id=args.llm) # Could use 'gpt-4o'

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
            print(f'<prompt>{prompts[0]}</prompt>')

        responses = []
            
        for sample, prompt in zip(batch_samples, prompts):
            tool = db_connectors[sample.db].as_smolagent_tool()
            agent = ToolCallingAgent(tools=[tool], model=model)
            responses.append(agent.run(prompt))

        if i == 0:
            print(f'<response>{responses[0]}</response>')
        for item, r in zip(batch_samples, responses):
            lines = r.strip().split('\n')
            if lines[0].startswith('```') and lines[-1].startswith('```'):
                r = '\n'.join(lines[1:-1])
            item.pred_query = r
            res.append(item)
        
    output_path = os.path.join(args.result_dir, f'result.json')
    with open(output_path, 'w') as fout:
        json.dump([item.model_dump(mode='json') for item in res], fout, indent=2)
    print(f'Saved result to {output_path}')


if __name__ == '__main__':
    main()

import os
import asyncio
from tqdm import tqdm


async def main():
    all_dirs = [d for d in os.listdir("output") if d.startswith("13")]
    for d in tqdm(all_dirs):
        # In every file under output/d recursively, not limited to json files, replace "intended_paramter_operator" with "intended_parameter_operator"
        for root, dirs, files in os.walk(os.path.join("output", d)):
            for file in files:
                print(os.path.join(root, file))
                with open(os.path.join(root, file), "r") as f:
                    content = f.read()
                content = content.replace("intended_paramter_operator", "intended_parameter_operator")
                with open(os.path.join(root, file), "w") as f:
                    f.write(content)


if __name__ == "__main__":
    asyncio.run(main())
